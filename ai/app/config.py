"""환경 설정. .env 파일에서 읽습니다 (.env.example 참고)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # 감정 엔진
    emotion_model_path: str = "models/orbit_emotion_v1.pth"  # cwd=ai/ 기준
    emotion_text_encoder: str = "klue/roberta-small"

    # STT
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # TTS
    tts_voice: str = "ko-KR-InJoonNeural"

    # 백엔드(Spring Boot)
    backend_base_url: str = "http://localhost:8080"
    # 맥락 조회가 응답 경로에 있으므로 짧게 둡니다. 넘기면 맥락 없이 응답합니다.
    backend_timeout_s: float = 3.0

    # 4단계 대중교통 판정 (docs/stage-mission-judgement.md 4단계)
    # 실내 테스트에서는 0 으로 두고 흐름만 확인. 시연·실사용은 5분 · 1km.
    transit_min_minutes: float = 5.0
    transit_min_km: float = 1.0
    # 사진 촬영 시각(captured_at)과 서버 수신 시각 차이 허용치. 예전 사진 재사용 방지
    transit_max_capture_age_s: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
