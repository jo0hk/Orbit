"""파트 간 계약이 깨지지 않았는지 확인하는 최소 테스트.

실행: cd ai && python -m pytest
"""

from app.schemas import Emotion, InteractResponse, Led, OledExpression, Vibe


def test_response_serializes_to_hw_contract():
    """LLM 응답이 HW가 기대하는 JSON 키를 갖는지."""
    res = InteractResponse(
        speech="치칙- 교신 감도 양호. 라저",
        led=Led.GREEN_SPARKLE,
        vibe=Vibe.DOUBLE_BUZZ,
        oled_expression=OledExpression.STAR_EYES,
    )
    payload = res.model_dump(mode="json")
    assert {"speech", "led", "vibe", "oled_expression"} <= payload.keys()


def test_emotion_labels_match_trained_model():
    """감정 모델이 출력하는 클래스와 enum이 일치하는지.

    TODO(1주차): happy 추가를 결정하면 이 테스트를 먼저 고치고 재학습하세요.
    """
    assert {e.value for e in Emotion} == {"sad", "anger", "fear", "disgust", "neutral"}
