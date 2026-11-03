"""감정 모델 출력 → 공통 감정값 변환.

규칙 근거: docs/interface-spec-v1.md 2절 (09-17 회의 공통 감정값, 10-01 제안)

감정 모델(Emotion)은 sad / anger / fear / disgust / neutral 5클래스이고
긍정 클래스가 없습니다. 재학습 없이 공통값(happy / sad / angry / calm)을
만들기 위해 두 단계로 바꿉니다.

  1. 라벨 매핑   sad·fear → sad, anger·disgust → angry, neutral → calm
  2. 긍정 보정   모델이 neutral이고 발화에 긍정 표현이 있으면 happy

보정은 neutral일 때만 합니다. 모델이 부정 감정을 냈는데 텍스트에
"좋아"가 있다고 happy로 덮으면, 억양에서 잡은 부정 신호를 버리게 됩니다.
"""

from __future__ import annotations

import re

from app.schemas import CommonEmotion, Emotion

_LABEL_MAP: dict[Emotion, CommonEmotion] = {
    Emotion.SAD: CommonEmotion.SAD,
    Emotion.FEAR: CommonEmotion.SAD,
    Emotion.ANGER: CommonEmotion.ANGRY,
    Emotion.DISGUST: CommonEmotion.ANGRY,
    Emotion.NEUTRAL: CommonEmotion.CALM,
}

# 공백을 지운 텍스트에서 찾습니다. 1단계 미션 기분 사전의 긍정 범주와 같은 출처입니다
# (docs/stage-mission-judgement.md 2절). "괜찮"·"편안"은 calm에 가까워 넣지 않았습니다.
POSITIVE_STEMS: tuple[str, ...] = (
    "좋",
    "기쁘", "기뻐", "기쁨",
    "행복",
    "신나", "신난", "신났", "신남",
    "설레", "설렘",
    "즐거", "즐겁",
    "상쾌",
    "뿌듯",
    "재밌", "재미있",
    "최고",
)

# 긍정 어간 바로 앞에 오면 부정: "안 좋아", "못 즐겼어"
_NEG_PREFIXES: tuple[str, ...] = ("안", "못")
# 긍정 어간 뒤 몇 글자 안에 있으면 부정: "좋지 않아", "기쁘지 못해", "좋은 일이 없어"
_NEG_SUFFIXES: tuple[str, ...] = ("않", "못", "없")
_NEG_SUFFIX_WINDOW = 5
# 어간 뒤에 오면 지금 상태가 아닌 바람이나 가정: "좋겠다", "좋을 텐데", "좋았으면"
_WISH_SUFFIXES: tuple[str, ...] = ("겠", "을텐데", "으면", "았으면")

_WHITESPACE = re.compile(r"\s+")


def has_positive_expression(text: str | None) -> bool:
    """부정·바람이 아닌 긍정 표현이 하나라도 있는지."""
    if not text:
        return False
    normalized = _WHITESPACE.sub("", text)

    for stem in POSITIVE_STEMS:
        start = normalized.find(stem)
        while start != -1:
            before = normalized[:start]
            after = normalized[start + len(stem):]
            negated = (
                before.endswith(_NEG_PREFIXES)
                or "별로" in before
                or any(n in after[:_NEG_SUFFIX_WINDOW] for n in _NEG_SUFFIXES)
            )
            wishful = after.startswith(_WISH_SUFFIXES)
            if not negated and not wishful:
                return True
            start = normalized.find(stem, start + 1)
    return False


def to_common_emotion(emotion: Emotion, text: str | None = None) -> CommonEmotion:
    """감정 모델 출력과 발화 텍스트로 공통 감정값을 정합니다."""
    common = _LABEL_MAP[emotion]
    if common is CommonEmotion.CALM and has_positive_expression(text):
        return CommonEmotion.HAPPY
    return common
