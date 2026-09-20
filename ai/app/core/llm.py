"""Gemini 2.5 Flash 호출. Strict JSON으로 speech/led/vibe를 동시 추출합니다.

1학기 교훈 (그대로 유지할 것):
  1. max_output_tokens로 자르지 마세요. JSON이 깨져 ServerError가 납니다.
     글자 수 제한은 프롬프트의 45자 규칙으로 겁니다.
  2. 503 UNAVAILABLE 대비 tenacity Exponential Backoff, 최대 3회.
  3. 완전 실패 시 예외 대신 비상 프로토콜 응답을 반환합니다.
"""

from __future__ import annotations

import json
import logging

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.schemas import InteractResponse, Led, OledExpression, Vibe

logger = logging.getLogger(__name__)

EMERGENCY_RESPONSE = InteractResponse(
    speech="치직- 통신 장애 발생. 태양풍 간섭으로 교신이 끊겼습니다. 오버.",
    led=Led.ORANGE,
    vibe=Vibe.SHORT,
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
        from google import genai

        key = self._settings.gemini_api_key
        if not key:
            # 1학기에 API_KEY=""로 돌려서 모든 호출이 실패했고,
            # 그 상태의 대기 시간이 레이턴시로 기록됐습니다. 같은 일을 막습니다.
            raise RuntimeError("GEMINI_API_KEY가 비어 있습니다. ai/.env를 확인하세요.")
        self._client = genai.Client(api_key=key)

    def _safety_settings(self):
        """3주차 정책 반영.

        1학기에는 4개 카테고리 전부 BLOCK_NONE이었습니다. HARASSMENT 완화는
        이유가 있습니다 - 적대적 발화("야 너 내가 만만해?")에 모델이 응답을
        거부하면 예외 대화 3번이 동작하지 않습니다.

        그러나 DANGEROUS_CONTENT까지 열어둘 이유는 없어 목록에서 제외했고,
        Gemini 기본 임계값이 적용됩니다. 자해 암시 발화는 그보다 앞서
        core/safety.py가 LLM 호출 전에 가로챕니다.
        """
        from google.genai import types

        c, t = types.HarmCategory, types.HarmBlockThreshold
        return [
            types.SafetySetting(category=cat, threshold=t.BLOCK_NONE)
            for cat in (
                c.HARM_CATEGORY_HARASSMENT,
                c.HARM_CATEGORY_HATE_SPEECH,
                c.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            )
        ]  # HARM_CATEGORY_DANGEROUS_CONTENT 는 기본값 유지

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def _call(self, system_prompt: str, user_text: str) -> dict:
        from google.genai import types

        response = self._client.models.generate_content(
            model=self._settings.gemini_model,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.3,
                safety_settings=self._safety_settings(),
            ),
        )
        return json.loads(response.text)

    def generate(self, system_prompt: str, user_text: str) -> InteractResponse:
        self._ensure_loaded()
        raw = self._call(system_prompt, user_text)

        # LLM이 enum에 없는 값을 지어내면 여기서 ValueError가 납니다.
        # pipeline이 잡아서 비상 프로토콜로 폴백합니다.
        stats = getattr(self._call, "retry", None)
        attempts = stats.statistics.get("attempt_number", 1) if stats else 1

        return InteractResponse(
            speech=raw["speech"],
            led=Led(raw["led"]),
            vibe=Vibe(raw["vibe"]),
            llm_retry_count=max(0, attempts - 1),
        )
