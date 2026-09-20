"""Orbit Core — 전체 파이프라인 오케스트레이션.

STT ➡️ 감정 분석 ➡️ 환경 분석 ➡️ LLM ➡️ TTS

단계별 소요 시간을 반드시 측정합니다. 2주차 대화 로그 스키마의 latency_ms가
이 값이고, 유효한 기준선을 세우는 유일한 수단입니다.

⚠️ 1학기의 "6초대"는 Gemini 호출이 실패한 상태에서 tenacity 백오프
   대기 시간을 포함해 잰 값이라 기준선으로 쓸 수 없습니다.
   1주차에 정상 응답 기준으로 다시 측정하세요.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager

from app.core.context import build_system_prompt
from app.core.emotion import EmotionEngine
from app.core.llm import EMERGENCY_RESPONSE, OrbitLLM
from app.core.stt import SpeechToText
from app.core.tts import RadioTTS
from app.schemas import EnvContext, InteractResponse, LatencyBreakdown, oled_for

logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs"


@contextmanager
def _timed(bucket: dict, key: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        bucket[key] = int((time.perf_counter() - start) * 1000)


class OrbitCore:
    """앱 기동 시 1회 생성하고 재사용합니다 (모델 로딩 비용 때문)."""

    def __init__(self) -> None:
        self.stt = SpeechToText()
        self.emotion = EmotionEngine()
        self.llm = OrbitLLM()
        self.tts = RadioTTS()

    def warmup(self) -> None:
        """기동 시 모델을 미리 올립니다. 첫 요청이 느려지는 것을 막습니다."""
        self.stt._ensure_loaded()
        self.emotion._ensure_loaded()

    async def interact(self, audio_path: str, ctx: EnvContext) -> InteractResponse:
        marks: dict[str, int] = {}
        total_start = time.perf_counter()

        with _timed(marks, "stt_ms"):
            user_text, stt_conf = self.stt.transcribe(audio_path)

        # TODO(최적화): 감정 분석은 STT 결과(텍스트)에 의존하므로 완전 병렬은
        #   불가능합니다. 오디오 특징 추출(librosa)만 STT와 병렬로 돌리면
        #   emotion_ms의 상당 부분을 감출 수 있습니다.
        with _timed(marks, "emotion_ms"):
            emotion, emo_conf = self.emotion.analyze(user_text, audio_path)

        system_prompt = build_system_prompt(emotion, ctx)

        with _timed(marks, "llm_ms"):
            try:
                result = self.llm.generate(system_prompt, user_text)
            except Exception:
                # 비상 프로토콜: 에러를 던지지 않고 멀티모달 폴백을 반환합니다.
                logger.warning("LLM 호출 실패. 비상 프로토콜로 응답합니다.", exc_info=True)
                result = EMERGENCY_RESPONSE.model_copy(deep=True)

        if not result.fallback_triggered:
            result.oled_expression = oled_for(emotion)

        with _timed(marks, "tts_ms"):
            out_path = f"{OUTPUT_DIR}/{uuid.uuid4().hex}.mp3"
            result.audio_url = await self.tts.synthesize(result.speech, out_path)

        result.user_text = user_text
        result.stt_confidence = stt_conf
        result.user_emotion = emotion
        result.user_emotion_confidence = emo_conf
        result.latency = LatencyBreakdown(
            **marks,
            total_ms=int((time.perf_counter() - total_start) * 1000),
        )

        logger.info(
            "interact 완료: emotion=%s conf=%.2f latency=%s",
            emotion.value, emo_conf or 0.0, result.latency.model_dump(),
        )
        return result
