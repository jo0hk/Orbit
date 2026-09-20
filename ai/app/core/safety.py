"""고위험 발화 탐지 및 고정 응답.

정책 문서: docs/high-risk-utterance-policy.md

설계 원칙 — **LLM에게 맡기지 않습니다.**
생성 모델의 출력은 매번 달라지고, 45자 제한과 페르소나 규칙이 걸려 있어
예측할 수 없습니다. 안전이 걸린 응답은 결정론적 경로로 처리합니다.

    음성 → STT → [고위험 탐지] ─── 해당 ──▶ 고정 응답 (LLM 건너뜀)
                      │
                    비해당
                      ▼
                감정분석 → LLM → TTS
"""

from __future__ import annotations

import re

from app.schemas import InteractResponse, Led, OledExpression, Vibe

# ─────────────────────────────────────────────────────────────
# 1차 탐지: 키워드
#
# ⚠️ 오탐을 허용합니다. 놓치는 것보다 낫습니다.
#    오탐 시 사용자는 조금 어색한 응답을 한 번 받을 뿐입니다.
#
#    알려진 오탐 사례: "죽을래?" 같은 적대적 농담도 여기 걸립니다.
#    3번 예외 대화(적대 발화)로 가야 할 발화가 이쪽으로 오지만,
#    의도적으로 이 방향을 택했습니다. 8주차 검증에서 빈도를 확인하세요.
# ─────────────────────────────────────────────────────────────
HIGH_RISK_KEYWORDS: tuple[str, ...] = (
    "죽고싶",
    "죽을래",
    "죽어버리",
    "사라지고싶",
    "자살",
    "자해",
    "살기싫",
    "없어지고싶",
    "끝내고싶",
    "뛰어내리",
)

_WHITESPACE = re.compile(r"\s+")


def detect_high_risk(text: str) -> bool:
    """1차 키워드 탐지.

    공백을 제거하고 비교하므로 "죽고 싶어" / "죽고싶어" 모두 잡힙니다.
    """
    if not text:
        return False
    normalized = _WHITESPACE.sub("", text)
    return any(kw in normalized for kw in HIGH_RISK_KEYWORDS)


# ─────────────────────────────────────────────────────────────
# 고정 응답
#
# 무전 톤을 의도적으로 벗어납니다. 캐릭터보다 사람이 우선입니다.
# 이 문구를 임의로 바꾸지 마십시오. 정책 문서를 먼저 고치세요.
# ─────────────────────────────────────────────────────────────
HIGH_RISK_SPEECH = """지금 많이 힘드신 것 같습니다.

혼자 견디지 않으셔도 됩니다.
아래로 연락하시면 전문 상담사와 바로 이야기할 수 있습니다.

자살예방 상담전화 109
정신건강 상담전화 1577-0199
청소년 상담전화 1388

24시간 연결됩니다."""


def build_high_risk_response() -> InteractResponse:
    """고위험 발화 대응 응답.

    하드웨어 신호는 차분하게 유지합니다.
    축하·경고 패턴(rainbow, strong_double, short)을 쓰지 않습니다.
    진동으로 놀라게 하지 않습니다.
    """
    return InteractResponse(
        speech=HIGH_RISK_SPEECH,
        led=Led.DIM_BLUE,
        vibe=Vibe.NONE,
        oled_expression=OledExpression.SAD_EYES,
        high_risk_detected=True,
    )
