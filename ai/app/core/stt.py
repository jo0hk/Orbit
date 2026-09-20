"""음성 → 텍스트.

1학기: openai-whisper. 단, 노트북 안에서 모델 크기가 엇갈렸습니다.
  - cell-1 독립 테스트: whisper.load_model("base")  ← 노션 일지에 기록된 값
  - OrbitCoreV4 실사용:  whisper.load_model("tiny") ← 실제로 돌아간 값
  노션에는 base로 적혀 있으나 파이프라인은 tiny로 동작했습니다.
  ⚠️ 1주차에 어느 쪽을 기준으로 삼을지 정하고 노션을 고치세요.

2학기: faster-whisper로 교체. GPU 없는 서버의 CPU 추론에서 약 4배 빠릅니다.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

# cell-1에서 쓰던 도메인 힌트. 고유명사 인식률을 올려주므로 유지합니다.
# OrbitCoreV4는 이걸 빠뜨리고 language만 넘겼습니다. 이식하며 복원했습니다.
INITIAL_PROMPT = "대장님, 오빗, 탐사 미션, 교신 시작, 오버."


class SpeechToText:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        s = self._settings
        logger.info("Whisper 로딩: size=%s device=%s", s.whisper_model_size, s.whisper_device)
        self._model = WhisperModel(
            s.whisper_model_size,
            device=s.whisper_device,
            compute_type=s.whisper_compute_type,
        )

    def transcribe(self, audio_path: str) -> tuple[str, float | None]:
        """returns (텍스트, 신뢰도).

        신뢰도는 세그먼트 avg_logprob의 평균을 exp로 환산한 값입니다.
        2주차 대화 로그의 stt_confidence로 저장됩니다.
        """
        self._ensure_loaded()

        segments, _info = self._model.transcribe(
            audio_path,
            language="ko",
            initial_prompt=INITIAL_PROMPT,
        )

        texts: list[str] = []
        logprobs: list[float] = []
        for seg in segments:  # generator이므로 순회해야 실제 추론이 돌아갑니다
            texts.append(seg.text)
            if seg.avg_logprob is not None:
                logprobs.append(seg.avg_logprob)

        text = "".join(texts).strip()
        confidence = None
        if logprobs:
            import math

            confidence = math.exp(sum(logprobs) / len(logprobs))

        return text, confidence
