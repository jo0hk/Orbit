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
    emotion_model_path: str = "ai/models/emotion_fusion.pt"
    emotion_text_encoder: str = "klue/roberta-small"

    # STT
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # TTS
    tts_voice: str = "ko-KR-InJoonNeural"

    # 백엔드(Spring Boot)
    backend_base_url: str = "http://localhost:8080"


@lru_cache
def get_settings() -> Settings:
    return Settings()
