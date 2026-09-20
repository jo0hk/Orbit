"""탐사 인증샷 칭찬 (4주차 산출물).

gemini-2.5-flash 멀티모달로 사진 속 객체를 인식하고 구체적인 찬사를 생성합니다.
1학기 실증: '벚꽃이 만개한 나무와 푸른 하늘' 인식 → 구체적 칭찬 생성 성공.

2학기 확장:
  - 7주차: GPS 이동 거리 / 날씨와 결합
  - 9주차: 반복 칭찬 방지 (최근 사용 문형 회피)
"""

from __future__ import annotations

import json
import logging

from app.config import get_settings
from app.schemas import InteractResponse, Led, OledExpression, Vibe

logger = logging.getLogger(__name__)

VISION_PROMPT = """
너는 은둔형 청년을 돕는 우주비행사 로봇 '오빗(Orbit)'이다.
대장님이 은둔의 방을 깨고 나와 탐사 미션(바깥 산책)을 수행하며 직접 찍어 보낸 사진이다.

[수칙]
1. 사진 속 요소(예: 맑은 하늘, 초록색 나무, 길고양이, 들꽃 등)를 최소 한 가지 이상 명확히 찾아내라.
2. 그 풍경을 구체적으로 언급하며, 바깥 정찰 미션을 멋지게 완수했다는 취지로
   무전 교신 톤의 깊은 찬사를 보내라.
3. 문장 끝에는 "치직-" 혹은 "오버."를 배치하고 Strict JSON 포맷으로만 출력하라.
4. "speech"는 공백 포함 45자 이내로 압축하라.

[응답 포맷]
{"speech": "대답 텍스트", "led": "rainbow", "vibe": "strong_double"}
"""

VISION_FALLBACK = InteractResponse(
    speech="치직- 대장님, 전송된 영상 데이터 유실로 분석에 실패했습니다. 오버.",
    led=Led.ORANGE,
    vibe=Vibe.SHORT,
    oled_expression=OledExpression.SAD_EYES,
    fallback_triggered=True,
)


class ExplorationVision:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None

    def _ensure_loaded(self) -> None:
        if self._client is not None:
            return
        from google import genai

        if not self._settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY가 비어 있습니다. ai/.env를 확인하세요.")
        self._client = genai.Client(api_key=self._settings.gemini_api_key)

    def praise(self, image_path: str, distance_m: int | None = None) -> InteractResponse:
        try:
            self._ensure_loaded()

            from google.genai import types
            from PIL import Image

            prompt = VISION_PROMPT
            # TODO(7주차): 거리/날씨를 프롬프트에 결합
            if distance_m:
                prompt += f"\n[참고] 대장님은 이번 탐사에서 {distance_m}m를 이동했다."

            response = self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=[Image.open(image_path), prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            raw = json.loads(response.text)
            return InteractResponse(
                speech=raw["speech"],
                led=Led(raw["led"]),
                vibe=Vibe(raw["vibe"]),
                oled_expression=OledExpression.STAR_EYES,
            )
        except Exception:
            logger.warning("비전 미션 실패: %s", image_path, exc_info=True)
            return VISION_FALLBACK.model_copy(deep=True)
