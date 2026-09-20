"""고위험 발화 대응 테스트.

이 테스트가 깨지면 안전 경로가 무너진 것입니다.
docs/high-risk-utterance-policy.md 를 먼저 읽고 고치세요.
"""

import pytest

from app.core.safety import (
    HIGH_RISK_SPEECH,
    build_high_risk_response,
    detect_high_risk,
)
from app.schemas import Led, OledExpression, Vibe


@pytest.mark.parametrize(
    "text",
    [
        "죽고 싶어",
        "죽고싶다",
        "그냥 사라지고 싶어",
        "자해했어",
        "살기 싫다",
        "이제 다 끝내고 싶어",
        "없어지고 싶어",
    ],
)
def test_detects_high_risk(text):
    assert detect_high_risk(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "오늘 좀 피곤해",
        "나가기 싫어",
        "야 너 내가 만만해?",
        "오빗 오늘 날씨 어때",
    ],
)
def test_ignores_normal_utterances(text):
    """일반 발화와 예외 대화 1~3번이 고위험으로 잡히지 않아야 합니다."""
    assert detect_high_risk(text) is False


def test_whitespace_is_normalized():
    assert detect_high_risk("죽 고 싶 어") is True


def test_response_signals_are_calm():
    """축하·경고 패턴을 쓰지 않습니다. 진동으로 놀라게 하지 않습니다."""
    res = build_high_risk_response()
    assert res.led is Led.DIM_BLUE
    assert res.vibe is Vibe.NONE
    assert res.oled_expression is OledExpression.SAD_EYES
    assert res.high_risk_detected is True


def test_response_drops_persona():
    """이 경우에만 무전 톤을 벗어납니다."""
    for token in ("치직", "대장님", "오버", "라저", "교신"):
        assert token not in HIGH_RISK_SPEECH


def test_response_includes_helplines():
    """상담 전화번호가 빠지면 응답의 의미가 없습니다."""
    for number in ("109", "1577-0199", "1388"):
        assert number in HIGH_RISK_SPEECH


def test_45_char_rule_does_not_apply():
    """45자 압축 규칙은 이 응답에 적용하지 않습니다."""
    assert len(HIGH_RISK_SPEECH) > 45
