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
from pathlib import Path

from app.config import get_settings
from app.missions import MAX_SPEECH_LEN
from app.schemas import InteractResponse, LandmarkReport, Led, OledExpression, Vibe

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 3단계 랜드마크 판독 (11-13)
#
# Gemini 호출 1회로 판독 항목(판정용)과 대사 후보 2개를 같이 받습니다.
# 판정 문서에는 "칭찬 엔진과 별도 호출"로 적었지만, 무료 한도(하루 약 20회)를
# 대화와 함께 쓰므로 호출을 하나로 합쳤습니다. 성공 여부는 여전히 코드 규칙
# (mission_judge.judge_landmark)이 정하고, 대사는 그 결과에 맞는 쪽만 씁니다.
# ─────────────────────────────────────────────────────────────
LANDMARK_PROMPT = """
너는 우주비행사 로봇 '오빗(Orbit)'의 관측 장비다.
은둔하던 대장님이 밖에 나가 동네 랜드마크(건물·조형물·간판)를 찍어 보낸 사진을 판독한다.

[판독 항목]
- is_outdoor: 야외에서 찍은 사진이면 true
- subject: 사진의 주 피사체 하나. building(건물) / structure(다리·탑 같은 구조물) /
  sculpture(조형물·동상) / signboard(간판·표지판) / person(사람) / other(그 외)
- people_prominent: 사람의 얼굴이나 몸이 사진의 주인공처럼 크게 찍혔으면 true
- confidence: subject 판독에 대한 확신 (0~1)
- description: 사진에서 가장 눈에 띄는 것을 20자 이내 한국어 명사구로 (예: "붉은 벽돌 교회 건물").
  사람의 생김새·옷차림은 묘사하지 마라.

[대사] 오빗의 무전 교신 대사 두 개를 함께 써라.
- speech_success: 사진 속 요소를 구체적으로 한 번 짚어 우주 스케일(은하·본부·탐사 일지)로 칭찬
- speech_retry: 건물·조형물·간판이 잘 보이게 찍어 달라는 부드러운 요청. 다시 할지는 대장님이 고르게
공통 규칙:
- 각 대사는 공백 포함 35자 안팎, 절대 45자를 넘기지 마라. 넘으면 그 대사는 버려진다.
- 한 문장만. "치직-"으로 시작, "오버" 또는 "라저"로 끝, 호칭은 "대장님".
- "실패"라는 단어를 쓰지 마라. speech_retry 에는 빨리·꼭·반드시·다시 해야·왜 를 쓰지 마라.
예 (길이 참고):
- speech_success: "치직- 붉은 벽돌 교회 포착! 탐사 일지에 기록합니다. 라저" (34자)
- speech_retry: "치직- 건물이 잘 안 보입니다. 한 장 더 부탁드립니다. 오버" (34자)
""".strip()

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 앱 권장 2MB. 여유를 두되 비정상 업로드는 거절


def _image_mime(data: bytes) -> str:
    """파일 앞부분으로 형식을 판별합니다. 확장자는 믿지 않습니다."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"  # 앱은 JPEG 로 보냄


_ENDINGS = ("오버", "라저", "교신 종료")
_RETRY_FORBIDDEN = ("빨리", "꼭", "반드시", "다시 해야", "왜")


def speech_follows_rules(speech: str, retry: bool = False) -> bool:
    """대사 규칙 (CLAUDE.md · persona.md): 45자 이내, 치직- 포함, 오버/라저/교신 종료로 끝,
    '실패' 금지, 재시도 대사의 재촉 표현 금지. 어기면 미리 써 둔 대사로 바꿉니다."""
    s = (speech or "").strip()
    if not s or len(s) > MAX_SPEECH_LEN or "치직" not in s or "실패" in s:
        return False
    if not s.rstrip(".!~ ").endswith(_ENDINGS):
        return False
    if retry and any(w in s for w in _RETRY_FORBIDDEN):
        return False
    return True

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
    led=Led.BLUE,
    vibe=Vibe.SHORT_PULSE,
    oled_expression=OledExpression.SAD,
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

    def inspect_landmark(self, image_path: str) -> LandmarkReport | None:
        """랜드마크 사진을 판독합니다. Gemini 호출이나 응답 형식이 잘못되면 None.

        None 이면 판정하지 않습니다(결과 API 호출 안 함, 다시 찍을 수 있음).
        """
        try:
            self._ensure_loaded()

            from google.genai import types

            # 파일을 그대로 보냅니다 (Pillow 의존성 없음). 앱이 긴 변 1280px·2MB 이하로
            # 줄이고 회전도 보정해서 보냅니다 (docs/app-ai-api.md 3절).
            data = Path(image_path).read_bytes()
            if len(data) > MAX_IMAGE_BYTES:
                logger.warning("사진이 너무 큼: %d bytes", len(data))
                return None
            image = types.Part.from_bytes(data=data, mime_type=_image_mime(data))

            response = self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=[image, LANDMARK_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LandmarkReport,
                    temperature=0.2,
                ),
            )
            return LandmarkReport.model_validate_json(response.text)
        except Exception:
            logger.warning("랜드마크 판독 실패", exc_info=True)
            return None

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
                oled_expression=OledExpression.HAPPY,
            )
        except Exception:
            logger.warning("비전 미션 실패: %s", image_path, exc_info=True)
            return VISION_FALLBACK.model_copy(deep=True)
