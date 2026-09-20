"""파트 간 계약이 깨지지 않았는지 확인하는 최소 테스트.

실행: cd ai && python -m pytest
"""

import pytest

from app.schemas import (
    Emotion,
    EnvContext,
    InteractResponse,
    Led,
    OledExpression,
    Vibe,
    oled_for,
)


def test_response_serializes_to_hw_contract():
    """LLM 응답이 HW가 기대하는 JSON 키를 갖는지."""
    res = InteractResponse(speech="치직- 교신 감도 양호. 오버.", led=Led.RAINBOW, vibe=Vibe.STRONG_DOUBLE)
    payload = res.model_dump(mode="json")
    assert {"speech", "led", "vibe", "oled_expression"} <= payload.keys()
    assert payload["led"] == "rainbow"


def test_hw_values_match_persona_prompt():
    """prompts/persona.md의 하드웨어 매핑 룰에 적힌 값과 enum이 일치하는지.

    프롬프트만 고치고 enum을 안 고치면 LLM 응답이 폐기되고 비상 프로토콜로
    떨어집니다. 그 반대도 마찬가지입니다.
    """
    assert {e.value for e in Led} == {"rainbow", "dim_blue", "dim_white", "orange"}
    assert {v.value for v in Vibe} == {"strong_double", "soft_continuous", "calm_wave", "short"}


def test_emotion_labels_match_trained_model():
    """감정 모델 체크포인트의 label_encoder와 일치해야 하는 클래스 집합.

    EmotionEngine이 기동 시 실제 체크포인트와 이 enum을 대조하고,
    다르면 RuntimeError로 중단합니다.

    TODO(1주차): happy 추가를 결정하면 이 테스트를 먼저 고치고 재학습하세요.
    """
    assert {e.value for e in Emotion} == {"sad", "anger", "fear", "disgust", "neutral"}


@pytest.mark.parametrize("emotion", list(Emotion))
def test_every_emotion_maps_to_an_expression(emotion):
    """감정이 추가돼도 OLED 매핑이 비지 않는지."""
    assert isinstance(oled_for(emotion), OledExpression)


def test_env_context_defaults_are_safe():
    """센서값이 하나도 안 왔을 때도 프롬프트 조립이 가능해야 합니다."""
    from app.core.context import build_system_prompt

    prompt = build_system_prompt(Emotion.NEUTRAL, EnvContext())
    assert "오빗" in prompt
    assert "neutral" in prompt
