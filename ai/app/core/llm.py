"""Gemini 2.5 Flash 호출. Strict JSON으로 speech/led/vibe를 동시 추출합니다.

1학기 교훈 (그대로 유지할 것):
  1. max_output_tokens로 자르지 마세요. JSON이 깨져 ServerError가 납니다.
     대신 프롬프트에 "45자 이내 압축 답변" 규칙을 넣습니다.
  2. 503 UNAVAILABLE 대비 tenacity로 2^n초 Exponential Backoff, 최대 3회.
  3. 완전 두절 시 에러 대신 비상 프로토콜 응답을 반환합니다.
"""

from __future__ import annotations

from app.config import get_settings
from app.schemas import InteractResponse, Led, OledExpression, Vibe

EMERGENCY_RESPONSE = InteractResponse(
    speech="치칙- 태양풍 간섭으로 교신이 끊겼습니다. 잠시 후 재시도 바랍니다. 오버",
    led=Led.ORANGE_PULSE,
    vibe=Vibe.TWO_SHORT_TAPS,
    oled_expression=OledExpression.SAD_EYES,
    fallback_triggered=True,
)


class OrbitLLM:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    def _ensure_loaded(self) -> None:
        if self._client is not None:
            return
        # TODO(1주차): Colab의 google-genai 클라이언트 초기화를 옮기세요.
        #
        # from google import genai
        # self._client = genai.Client(api_key=self._settings.gemini_api_key)
        raise NotImplementedError("1주차 이식 대상: Gemini 클라이언트")

    # TODO(1주차): @retry(wait=wait_exponential(), stop=stop_after_attempt(3)) 적용
    def generate(self, system_prompt: str, user_text: str) -> InteractResponse:
        """response_mime_type="application/json" 으로 Strict JSON을 강제합니다."""
        self._ensure_loaded()
        raise NotImplementedError
