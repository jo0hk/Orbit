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

from app.core.backend_client import BackendClient, BackendContext
from app.core.context import build_system_prompt
from app.core.emotion import EmotionEngine
from app.core.emotion_map import to_common_emotion
from app.core.llm import EMERGENCY_RESPONSE, OrbitLLM
from app.core.safety import build_high_risk_response, detect_high_risk
from app.core.stt import SpeechToText
from app.core.tts import RadioTTS
from app.core.turn import MISSION_SIGNAL, TurnRecord, judge_turn
from app.missions import Channel
from app.schemas import (
    Emotion,
    EnvContext,
    InteractResponse,
    LatencyBreakdown,
    MissionResult,
    oled_for,
)

logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs"
# 최근 대화는 아직 프롬프트에 쓰지 않으므로 조회하지 않습니다.
# 프롬프트 주입 규칙을 정하면 값을 올리세요 (docs/conversation-log-spec.md).
RECENT_TURNS_FOR_PROMPT = 0


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
        self.backend = backend

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
                out_path = f"{OUTPUT_DIR}/{uuid.uuid4().hex}.mp3"
                try:
                    # 고위험 대응은 무전 노이즈 없이 평범한 목소리로 출력합니다.
                    result.audio_url = await self.tts.synthesize(
                        result.speech, out_path, plain=high_risk
                    )
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
