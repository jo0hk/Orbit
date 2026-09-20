"""음성 → 텍스트.

1학기: openai-whisper (base), Colab T4 GPU.
2학기: faster-whisper로 교체. GPU 없는 서버의 CPU 추론에서 약 4배 빠릅니다.

⚠️ 1주차 작업: Colab GPU 기준과 서버 CPU 기준 STT 단독 레이턴시를
   각각 측정해서 노션 2학기 계획 페이지에 기록하세요.
"""

from __future__ import annotations

from app.config import get_settings


class SpeechToText:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None  # lazy load

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # TODO(1주차): Colab 노트북의 whisper 로딩 셀을 여기로 옮기세요.
        #
        # from faster_whisper import WhisperModel
        # self._model = WhisperModel(
        #     self._settings.whisper_model_size,
        #     device=self._settings.whisper_device,
        #     compute_type=self._settings.whisper_compute_type,
        # )
        raise NotImplementedError("1주차 이식 대상: faster-whisper 모델 로딩")

    def transcribe(self, audio_path: str) -> tuple[str, float | None]:
        """returns (텍스트, 신뢰도). 신뢰도는 2주차 로그의 stt_confidence."""
        self._ensure_loaded()
        # TODO(1주차): segments를 합치고 avg_logprob를 confidence로 환산
        raise NotImplementedError
