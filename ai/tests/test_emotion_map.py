"""감정 모델 출력 → 공통 감정값 변환 테스트.

규칙: docs/interface-spec-v1.md 2절. 백엔드 Emotion enum이 공통값 4개만 받으므로
이 변환이 틀리면 대화 저장이 거부됩니다.
"""

import pytest

from app.core.emotion_map import has_positive_expression, to_common_emotion
from app.schemas import CommonEmotion, Emotion, InteractResponse, Led, Vibe


def test_common_emotion_values_match_backend():
    """백엔드 Emotion enum(@JsonValue 소문자)과 같은 집합이어야 합니다."""
    assert {e.value for e in CommonEmotion} == {"happy", "sad", "angry", "calm"}


@pytest.mark.parametrize(
    ("model_label", "expected"),
    [
        (Emotion.SAD, CommonEmotion.SAD),
        (Emotion.FEAR, CommonEmotion.SAD),
        (Emotion.ANGER, CommonEmotion.ANGRY),
        (Emotion.DISGUST, CommonEmotion.ANGRY),
        (Emotion.NEUTRAL, CommonEmotion.CALM),
    ],
)
def test_label_mapping_without_text(model_label, expected):
    assert to_common_emotion(model_label) is expected


@pytest.mark.parametrize("model_label", list(Emotion))
def test_every_model_label_maps(model_label):
    """감정 클래스가 추가되면 매핑도 추가해야 합니다. 누락 시 KeyError로 드러납니다."""
    assert isinstance(to_common_emotion(model_label, "아무 말"), CommonEmotion)


@pytest.mark.parametrize(
    "text",
    [
        "오늘 기분 좋아",
        "좋은 아침",
        "안녕 좋은 하루야",
        "너무 행복해",
        "오늘 진짜 신났어",
        "내일 여행이라 설레",
        "뿌듯하다",
        "재밌었어",
        "기뻐",
        "오늘 좋았음",
        "산책 좋았어",
    ],
)
def test_neutral_with_positive_text_becomes_happy(text):
    assert to_common_emotion(Emotion.NEUTRAL, text) is CommonEmotion.HAPPY


@pytest.mark.parametrize(
    "text",
    [
        "안 좋아",
        "기분 안좋아",
        "별로 좋지 않아",
        "좋지 않은 하루",
        "행복하지 않아",
        "하나도 못 즐겼어",
        "좋은 일이 없어",
        "기분이 좋았으면 좋겠다",
        "그냥 그래",
        "괜찮아",
        "",
    ],
)
def test_neutral_without_positive_expression_stays_calm(text):
    assert to_common_emotion(Emotion.NEUTRAL, text) is CommonEmotion.CALM


@pytest.mark.parametrize("model_label", [Emotion.SAD, Emotion.FEAR, Emotion.ANGER, Emotion.DISGUST])
def test_positive_text_does_not_override_negative_model_output(model_label):
    """억양에서 잡은 부정 신호를 텍스트로 덮지 않습니다. 보정은 neutral일 때만."""
    assert to_common_emotion(model_label, "좋아") is not CommonEmotion.HAPPY


def test_none_text_is_safe():
    assert has_positive_expression(None) is False
    assert to_common_emotion(Emotion.NEUTRAL, None) is CommonEmotion.CALM


def test_response_carries_both_labels():
    """응답에 원래 라벨(user_emotion)과 공통값(emotion)이 모두 직렬화되어야 합니다."""
    res = InteractResponse(speech="치직- 수신 완료. 오버.", led=Led.RAINBOW, vibe=Vibe.STRONG_DOUBLE)
    payload = res.model_dump(mode="json")
    assert payload["user_emotion"] == "neutral"
    assert payload["emotion"] == "calm"
