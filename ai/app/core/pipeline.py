"""Orbit Core — 전체 파이프라인 오케스트레이션.

STT ➡️ 감정 분석 ➡️ 환경 분석 ➡️ LLM ➡️ TTS

단계별 소요 시간을 반드시 측정합니다. 2주차 대화 로그 스키마의 latency_ms가
이 값이고, 6초대 기준선이 깨지는 지점을 찾는 유일한 수단입니다.
"""

from __future__ import annotations

import time
from contextlib import contextmanager

from app.core.context import build_system_prompt
from app.core.emotion import EmotionEngine
from app.core.llm import EMERGENCY_RESPONSE, OrbitLLM
from app.core.stt import SpeechToText
from app.core.tts import RadioTTS
from app.schemas import EnvContext, InteractResponse, LatencyBreakdown


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

    async def interact(self, audio_path: str, ctx: EnvContext) -> InteractResponse:
        marks: dict[str, int] = {}
        total_start = time.perf_counter()

        with _timed(marks, "stt_ms"):
            user_text, stt_conf = self.stt.transcribe(audio_path)

        # TODO(3주차): 감정 분석을 STT와 병렬 수행하면 레이턴시를 줄일 수 있습니다.
        #   1학기 설계 의도는 병렬이었으나 현재는 순차입니다.
        with _timed(marks, "emotion_ms"):
            emotion, emo_conf = self.emotion.analyze(user_text, audio_path)

        system_prompt = build_system_prompt(emotion, ctx)

        with _timed(marks, "llm_ms"):
            try:
                result = self.llm.generate(system_prompt, user_text)
            except Exception:
                # 비상 프로토콜: 에러를 던지지 않고 멀티모달 폴백을 반환합니다.
                result = EMERGENCY_RESPONSE.model_copy(deep=True)

        with _timed(marks, "tts_ms"):
            result.audio_url = await self.tts.synthesize(result.speech, out_path="outputs/reply.wav")

        result.user_text = user_text
        result.stt_confidence = stt_conf
        result.emotion = emotion
        result.emotion_confidence = emo_conf
        result.latency = LatencyBreakdown(
            **marks,
            total_ms=int((time.perf_counter() - total_start) * 1000),
        )
        return result
