"""Orbit Core — 전체 파이프라인 오케스트레이션.

STT ➡️ 감정 분석 ➡️ 환경 분석 ➡️ LLM ➡️ TTS

단계별 소요 시간을 반드시 측정합니다. 2주차 대화 로그 스키마의 latency_ms가
이 값이고, 유효한 기준선을 세우는 유일한 수단입니다.

⚠️ 1학기의 "6초대"는 Gemini 호출이 실패한 상태에서 tenacity 백오프
   대기 시간을 포함해 잰 값이라 기준선으로 쓸 수 없습니다.
   1주차에 정상 응답 기준으로 다시 측정하세요.

백엔드 연동 (docs/interface-spec-v1.md 1절, docs/mission-context-injection.md 2-1절):
  - 키링 음성: device_id → 백엔드 맥락 조회 → 미션 판정 → 응답
  - 앱 텍스트: user_id → 같은 흐름 (STT·TTS 없음)
  - 결과 API 호출과 대화 저장은 응답 후 백그라운드(app/core/turn.py persist_turn)
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.core.backend_client import BackendClient, BackendContext
from app.core.context import build_system_prompt
from app.core.emotion import EmotionEngine
from app.core.emotion_map import to_common_emotion
from app.core.llm import EMERGENCY_RESPONSE, OrbitLLM
from app.core.safety import build_high_risk_response, detect_high_risk
from app.core.stt import SpeechToText
from app.config import get_settings
from app.core.mission_judge import distance_km, judge_landmark, judge_transit, transit_boarding_ok
from app.core.tts import RadioTTS
from app.core.turn import MISSION_SIGNAL, MissionTurn, TurnRecord, judge_turn
from app.core.vision import VISION_FALLBACK, ExplorationVision, speech_follows_rules
from app.missions import BY_TYPE, Channel, MissionType, ReasonCode
from app.schemas import (
    CommonEmotion,
    Emotion,
    EnvContext,
    InteractResponse,
    LatencyBreakdown,
    Led,
    MissionResult,
    OledExpression,
    Vibe,
    oled_for,
)

logger = logging.getLogger(__name__)

# 응답 음성 저장 위치. main.py 가 이 폴더를 /outputs 로 공개하고,
# 키링은 audio_url("outputs/<파일>.wav") 앞에 서버 주소를 붙여 내려받습니다.
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"  # ai/outputs
OUTPUT_URL_PREFIX = "outputs"
# 최근 대화는 아직 프롬프트에 쓰지 않으므로 조회하지 않습니다.
# 프롬프트 주입 규칙을 정하면 값을 올리세요 (docs/conversation-log-spec.md).
RECENT_TURNS_FOR_PROMPT = 0

# ─── 사진 판정 고정 대사 (45자 규칙 확인: 30~36자) ───────────────
KST = timezone(timedelta(hours=9))  # 백엔드 미션 배정 날짜 기준 (Asia/Seoul)
PHOTO_PEOPLE_RETRY = "치직- 사람 말고 건물이나 조형물을 담아 주시겠습니까. 오버"
PHOTO_LIMIT_SPEECH = "치직- 오늘 관측 장비가 과열됐습니다. 내일 송신 바랍니다. 오버"
# 4단계 (11-20)
TRANSIT_BOARDING_OK = "치직- 탑승 확인! 내리면 정류장이나 역명판을 송신 바랍니다. 오버"
TRANSIT_BOARDING_RETRY = "치직- 교통카드 단말기나 하차벨을 담아 주시겠습니까. 오버"
TRANSIT_NEED_BOARDING = "치직- 승차 인증부터 송신해 주십시오. 오버"
TRANSIT_STALE_PHOTO = "치직- 방금 찍은 사진만 인정됩니다. 새로 촬영 바랍니다. 오버"
TRANSIT_NEED_LOCATION = "치직- 위치 신호가 없습니다. 위치 권한을 켜 주십시오. 오버"


@dataclass
class _Boarding:
    """승차 인증 기록. 메모리에만 두고, 하차 성공·날짜 변경 시 버립니다(좌표 저장 금지)."""

    day: date
    captured_at: datetime
    lat: float
    lng: float


def _parse_captured_at(raw: str | None) -> datetime | None:
    """ISO 8601 촬영 시각. 시간대가 없으면 한국 시간으로 봅니다."""
    if not raw:
        return None
    try:
        t = datetime.fromisoformat(raw.strip())
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=KST)
PHOTO_PRAISE_DEFAULT = "치직- 관측 사진 수신! 탐사 일지에 기록했습니다, 대장님. 라저"


@contextmanager
def _timed(bucket: dict, key: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        bucket[key] = int((time.perf_counter() - start) * 1000)


@dataclass
class TurnOutcome:
    """엔드포인트로 돌려주는 것: 사용자 응답 + 응답 후 백엔드에 남길 기록."""

    response: InteractResponse
    record: TurnRecord


class OrbitCore:
    """앱 기동 시 1회 생성하고 재사용합니다 (모델 로딩 비용 때문)."""

    def __init__(self, backend: BackendClient | None = None) -> None:
        self.stt = SpeechToText()
        self.emotion = EmotionEngine()
        self.llm = OrbitLLM()
        self.tts = RadioTTS()
        self.vision = ExplorationVision()
        self.backend = backend
        # 3단계 사진 판정 하루 횟수 (사용자, 날짜) → 횟수. 서버를 재시작하면 초기화됩니다.
        self._photo_judges: dict[tuple[int, date], int] = {}
        # 4단계: 판정 횟수 (사용자, 날짜, 승차/하차) → 횟수, 승차 기록 사용자 → _Boarding
        self._transit_judges: dict[tuple[int, date, str], int] = {}
        self._boardings: dict[int, _Boarding] = {}
        s = get_settings()
        self.transit_min_minutes = s.transit_min_minutes
        self.transit_min_km = s.transit_min_km
        self.transit_max_capture_age_s = s.transit_max_capture_age_s

    def warmup(self) -> None:
        """기동 시 모델을 미리 올립니다. 첫 요청이 느려지는 것을 막습니다."""
        self.stt._ensure_loaded()
        self.emotion._ensure_loaded()

    async def _fetch_context(
        self, *, device_id: str | None = None, user_id: int | None = None
    ) -> BackendContext:
        if self.backend is None:
            return BackendContext(user_id=user_id)
        return await self.backend.fetch_context(
            device_id=device_id, user_id=user_id, recent_limit=RECENT_TURNS_FOR_PROMPT
        )

    # ─── 키링 음성 ────────────────────────────────────────
    async def interact_voice(
        self,
        audio_path: str,
        *,
        device_id: str,
        lux: int | None = None,
        request_id: str | None = None,
    ) -> TurnOutcome:
        marks: dict[str, int] = {}
        total_start = time.perf_counter()

        with _timed(marks, "stt_ms"):
            user_text, stt_conf = self.stt.transcribe(audio_path)

        # TODO(최적화): 맥락 조회는 STT와 무관하므로 STT를 스레드로 돌리면 겹칠 수 있습니다.
        with _timed(marks, "context_ms"):
            bctx = await self._fetch_context(device_id=device_id)

        # TODO(최적화): 감정 분석은 STT 결과(텍스트)에 의존하므로 완전 병렬은
        #   불가능합니다. 오디오 특징 추출(librosa)만 STT와 병렬로 돌리면
        #   emotion_ms의 상당 부분을 감출 수 있습니다.
        with _timed(marks, "emotion_ms"):
            emotion, emo_conf = self.emotion.analyze(user_text, audio_path)

        return await self._respond(
            channel=Channel.VOICE,
            user_text=user_text,
            stt_conf=stt_conf,
            emotion=emotion,
            emo_conf=emo_conf,
            env=EnvContext(lux=lux, weather=bctx.weather),
            bctx=bctx,
            request_id=request_id,
            synthesize=True,
            marks=marks,
            total_start=total_start,
        )

    # ─── 앱 텍스트 ────────────────────────────────────────
    async def interact_text(
        self,
        text: str,
        *,
        user_id: int,
        request_id: str | None = None,
    ) -> TurnOutcome:
        marks: dict[str, int] = {}
        total_start = time.perf_counter()

        with _timed(marks, "context_ms"):
            bctx = await self._fetch_context(user_id=user_id)

        # 감정 모델은 음성 특징을 함께 받도록 학습되어 텍스트만으로는 돌리지 않습니다.
        # neutral 로 두고, 공통값 변환에서 긍정 표현이면 happy 로 보정됩니다.
        # TODO: 텍스트 전용 감정 판단 방법 결정 (8주차 오분류 수집과 함께)
        return await self._respond(
            channel=Channel.TEXT,
            user_text=text,
            stt_conf=None,
            emotion=Emotion.NEUTRAL,
            emo_conf=None,
            env=EnvContext(weather=bctx.weather),
            bctx=bctx,
            request_id=request_id,
            synthesize=False,  # 앱은 글로 보여 줍니다. TTS 시간을 쓰지 않습니다.
            marks=marks,
            total_start=total_start,
        )

    # ─── 앱 사진 (11-13 3단계 랜드마크, 11-20 4단계 대중교통) ──────
    async def interact_photo(
        self,
        image_path: str,
        *,
        user_id: int,
        request_id: str | None = None,
        step: str | None = None,
        captured_at: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
    ) -> TurnOutcome:
        """사진을 판독해 3·4단계 미션을 판정하고 오빗 대사를 돌려줍니다.

        - 오늘 미션이 3단계(LANDMARK_PHOTO) 진행 중이면 판정 → 결과 API (응답 후)
        - 4단계(TRANSIT)는 승차 → 하차 두 장 (_transit_turn)
        - 사진 미션이 아닌 날에는 판정 없이 사진만 칭찬
        Gemini 는 사진 한 장당 1회 씁니다. 음성 합성은 하지 않습니다(앱 표시용).
        """
        marks: dict[str, int] = {}
        total_start = time.perf_counter()
        request_id = request_id or uuid.uuid4().hex

        with _timed(marks, "context_ms"):
            bctx = await self._fetch_context(user_id=user_id)

        today = bctx.mission
        active_type = today.mission_type if today is not None and today.in_progress else None
        landmark = BY_TYPE[MissionType.LANDMARK_PHOTO]
        key = (user_id, datetime.now(KST).date())

        mission_turn: MissionTurn | None = None
        description = ""
        if active_type is MissionType.TRANSIT:
            result, mission_turn, description = self._transit_turn(
                image_path, today.mission_id, user_id, step, captured_at, lat, lng, marks
            )
        elif (
            active_type is MissionType.LANDMARK_PHOTO
            and self._photo_judges.get(key, 0) >= (landmark.daily_judge_limit or 0)
        ):
            result = self._photo_reply(PHOTO_LIMIT_SPEECH, MissionResult.NONE)
        else:
            with _timed(marks, "llm_ms"):
                report = self.vision.inspect_landmark(image_path)
            if report is None:
                # 판독 실패: 판정하지 않음 (결과 API 호출 안 함, 다시 찍을 수 있음)
                result = VISION_FALLBACK.model_copy(deep=True)
            else:
                description = report.description
                if active_type is MissionType.LANDMARK_PHOTO:
                    self._photo_judges[key] = self._photo_judges.get(key, 0) + 1
                    judgement = judge_landmark(report)
                    mission_turn = MissionTurn(today.mission_id, landmark, judgement)
                    speech = self._landmark_speech(report, judgement.reason)
                    result = self._photo_reply(speech, judgement.result)
                else:
                    praise = report.speech_success
                    if not speech_follows_rules(praise):
                        praise = PHOTO_PRAISE_DEFAULT
                    result = self._photo_reply(praise, MissionResult.NONE)

        result.user_text = f"[사진] {description}".strip()
        result.emotion = CommonEmotion.CALM
        result.request_id = request_id
        result.latency = LatencyBreakdown(
            **marks, total_ms=int((time.perf_counter() - total_start) * 1000)
        )
        logger.info(
            "interact 완료: channel=PHOTO mission=%s reason=%s latency=%s",
            result.mission_result.value,
            mission_turn.judgement.reason.value if mission_turn and mission_turn.judgement.reason else None,
            result.latency.model_dump(),
        )

        record = TurnRecord(
            user_id=bctx.user_id,
            request_id=request_id,
            channel=Channel.PHOTO,
            user_text=result.user_text,
            orbit_speech=result.speech,
            emotion=None,  # 사진에는 사용자 감정이 없음
            stage=bctx.stage,
            mission_turn=mission_turn,
        )
        return TurnOutcome(response=result, record=record)

    def _transit_turn(self, image_path, mission_id, user_id, step, captured_at, lat, lng, marks):
        """4단계 한 장 처리. 반환: (응답, 판정 or None, 사진 묘사).

        Gemini 를 부르기 전에 촬영 시각·위치·승차 기록을 먼저 확인해 한도를 아낍니다.
        좌표는 거리 계산에만 쓰고 로그·DB 에 남기지 않습니다.
        """
        transit = BY_TYPE[MissionType.TRANSIT]
        now = datetime.now(KST)
        today = now.date()
        reply = self._photo_reply

        shot = _parse_captured_at(captured_at)
        if shot is None or abs((now - shot).total_seconds()) > self.transit_max_capture_age_s:
            return reply(TRANSIT_STALE_PHOTO, MissionResult.NONE), None, ""
        if lat is None or lng is None:
            return reply(TRANSIT_NEED_LOCATION, MissionResult.NONE), None, ""

        boarding = self._boardings.get(user_id)
        if boarding is not None and boarding.day != today:
            self._boardings.pop(user_id, None)  # 날짜가 바뀌면 승차부터 다시
            boarding = None
        step = (step or "").strip().lower()
        if step not in ("boarding", "alighting"):
            step = "alighting" if boarding else "boarding"
        if step == "alighting" and boarding is None:
            return reply(TRANSIT_NEED_BOARDING, MissionResult.NONE), None, ""

        key = (user_id, today, step)
        if self._transit_judges.get(key, 0) >= (transit.daily_judge_limit or 0):
            return reply(PHOTO_LIMIT_SPEECH, MissionResult.NONE), None, ""

        with _timed(marks, "llm_ms"):
            report = self.vision.inspect_transit(image_path, step)
        if report is None:
            return VISION_FALLBACK.model_copy(deep=True), None, ""
        self._transit_judges[key] = self._transit_judges.get(key, 0) + 1

        if step == "boarding":
            if not transit_boarding_ok(report):
                return reply(TRANSIT_BOARDING_RETRY, MissionResult.NONE), None, report.description
            self._boardings[user_id] = _Boarding(today, shot, lat, lng)
            res = reply(TRANSIT_BOARDING_OK, MissionResult.NONE)
            res.next_step = "alighting"  # 앱이 하차 촬영 단계로 넘어감. 결과 API 는 아직 안 부름
            return res, None, report.description

        minutes = (shot - boarding.captured_at).total_seconds() / 60
        km = distance_km(boarding.lat, boarding.lng, lat, lng)
        judgement = judge_transit(report, minutes, km, self.transit_min_minutes, self.transit_min_km)
        if judgement.result is MissionResult.SUCCESS:
            self._boardings.pop(user_id, None)
            s = report.speech_success
            speech = s if speech_follows_rules(s) else transit.success[0]
        elif judgement.reason is ReasonCode.TRANSIT_PHOTO:
            s = report.speech_retry
            speech = s if speech_follows_rules(s, retry=True) else transit.retry[1]
        else:  # 시간·거리 미달: 승차 기록은 유지 (더 타고 가서 다시 찍을 수 있음)
            speech = transit.retry[0]
        res = reply(speech, judgement.result)
        if judgement.result is not MissionResult.SUCCESS:
            res.next_step = "alighting"
        return res, MissionTurn(mission_id, transit, judgement), report.description

    @staticmethod
    def _photo_reply(speech: str, mission_result: MissionResult) -> InteractResponse:
        signal = MISSION_SIGNAL.get(mission_result)
        if signal is not None:
            led, vibe, oled = signal.led, signal.vibe, signal.oled
        else:  # 판정 없는 칭찬·안내
            led, vibe, oled = Led.RAINBOW, Vibe.STRONG_DOUBLE, OledExpression.HAPPY
        return InteractResponse(
            speech=speech, led=led, vibe=vibe, oled_expression=oled, mission_result=mission_result
        )

    @staticmethod
    def _landmark_speech(report, reason: ReasonCode | None) -> str:
        """판정 결과에 맞는 대사. Gemini 대사가 규칙을 어기면 미리 써 둔 대사를 씁니다."""
        mission = BY_TYPE[MissionType.LANDMARK_PHOTO]
        if reason is ReasonCode.LANDMARK_OK:
            s = report.speech_success
            return s if speech_follows_rules(s) else mission.success[0]
        if reason is ReasonCode.LANDMARK_PEOPLE:
            return PHOTO_PEOPLE_RETRY
        if reason is ReasonCode.LANDMARK_INDOOR:
            return mission.retry[0]
        s = report.speech_retry
        return s if speech_follows_rules(s, retry=True) else mission.retry[1]

    # ─── 공통 ─────────────────────────────────────────────
    async def _respond(
        self,
        *,
        channel: Channel,
        user_text: str,
        stt_conf: float | None,
        emotion: Emotion,
        emo_conf: float | None,
        env: EnvContext,
        bctx: BackendContext,
        request_id: str | None,
        synthesize: bool,
        marks: dict[str, int],
        total_start: float,
    ) -> TurnOutcome:
        request_id = request_id or uuid.uuid4().hex
        high_risk = detect_high_risk(user_text)

        # 판정은 응답 전에 같은 턴에서 합니다. 판정과 축하가 한 응답에 담깁니다.
        mission_turn = judge_turn(bctx, channel, user_text, stt_conf, high_risk=high_risk)
        mission_result = mission_turn.judgement.result if mission_turn else MissionResult.NONE
        if mission_turn is not None:
            env.mission_id = str(mission_turn.mission_id)
            env.mission_type = mission_turn.mission.mission_type.value
            env.mission_result = mission_result
            reason = mission_turn.judgement.reason
            env.mission_reason = reason.value if reason else None

        if high_risk:
            # LLM을 호출하지 않습니다. 생성 모델의 출력은 매번 달라지므로
            # 안전이 걸린 응답에 쓸 수 없습니다.
            # 감정 분석은 그대로 수행합니다 - 정책 문서의 2차 탐지 기준
            # (sad/fear가 연속 5턴 지속)이 이 기록을 필요로 합니다.
            logger.warning("고위험 발화 탐지. LLM을 건너뛰고 고정 응답을 반환합니다.")
            result = build_high_risk_response()
        else:
            system_prompt = build_system_prompt(emotion, env)

            with _timed(marks, "llm_ms"):
                try:
                    result = self.llm.generate(system_prompt, user_text)
                except Exception:
                    # 비상 프로토콜: 에러를 던지지 않고 멀티모달 폴백을 반환합니다.
                    logger.warning("LLM 호출 실패. 비상 프로토콜로 응답합니다.", exc_info=True)
                    result = EMERGENCY_RESPONSE.model_copy(deep=True)

            if not result.fallback_triggered:
                signal = MISSION_SIGNAL.get(mission_result)
                if signal is not None:
                    # 미션 반응 턴은 서버가 HW 신호를 정합니다 (mission-context-injection.md 3-6절).
                    # 성공 턴에 사용자 감정 때문에 슬픈 표정이 나가지 않게 합니다.
                    result.led = signal.led
                    result.vibe = signal.vibe
                    result.oled_expression = signal.oled
                else:
                    result.oled_expression = oled_for(emotion)

        if synthesize:
            with _timed(marks, "tts_ms"):
                name = f"{uuid.uuid4().hex}.wav"  # 16kHz 모노 16bit WAV (키링 재생 형식)
                try:
                    # 고위험 대응은 무전 노이즈 없이 평범한 목소리로 출력합니다.
                    await self.tts.synthesize(
                        result.speech, str(OUTPUT_DIR / name), plain=high_risk
                    )
                    result.audio_url = f"{OUTPUT_URL_PREFIX}/{name}"
                except Exception:
                    # 음성 합성(edge-tts, 외부 서비스)이 실패해도 대사·HW 신호는 내보내고
                    # 대화도 저장합니다. audio_url 이 null 이면 음성 없이 응답한 것입니다.
                    logger.warning("TTS 실패. 음성 없이 응답합니다.", exc_info=True)
                    result.audio_url = None

        result.user_text = user_text
        result.stt_confidence = stt_conf
        result.user_emotion = emotion
        result.user_emotion_confidence = emo_conf
        # 앱·백엔드용 공통 감정값. 대화 저장 시 이 값을 씁니다 (docs/interface-spec-v1.md 2절)
        result.emotion = to_common_emotion(emotion, user_text)
        result.mission_result = mission_result
        result.request_id = request_id
        result.latency = LatencyBreakdown(
            **marks,
            total_ms=int((time.perf_counter() - total_start) * 1000),
        )

        logger.info(
            "interact 완료: channel=%s emotion=%s(%s) conf=%.2f high_risk=%s mission=%s latency=%s",
            channel.value, emotion.value, result.emotion.value, emo_conf or 0.0, high_risk,
            mission_result.value, result.latency.model_dump(),
        )

        record = TurnRecord(
            user_id=bctx.user_id,
            request_id=request_id,
            channel=channel,
            user_text=user_text,
            orbit_speech=result.speech,
            emotion=result.emotion,
            stage=bctx.stage,
            mission_turn=mission_turn,
        )
        return TurnOutcome(response=result, record=record)
