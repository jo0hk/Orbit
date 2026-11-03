"""1·2단계 미션 규칙 판정.

규칙 근거: docs/stage-mission-judgement.md 2절

LLM을 쓰지 않습니다. 같은 입력에 같은 판정이 나와야 결과 API 기록과
회귀 테스트를 믿을 수 있기 때문입니다. 3·4단계(사진)는 Vision 판정이라
업로드 경로가 정해진 뒤 추가합니다.

호출 전제:
  - 고위험 발화는 pipeline이 먼저 가로챕니다. 여기로 오지 않습니다.
  - 오늘 미션이 IN_PROGRESS 이고 입력 채널이 미션과 일치할 때만 호출합니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.missions import ReasonCode
from app.schemas import MissionResult, WeatherCategory

STT_MIN_CONFIDENCE = 0.5  # 미만이면 판정하지 않고 예외 대화 5번(되묻기)

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Judgement:
    result: MissionResult  # SUCCESS / RETRY / DEFERRED
    reason: ReasonCode | None  # DEFERRED(거부)는 결과 API를 호출하지 않으므로 None
    confidence: float = 1.0  # 규칙 판정은 1.0


def _normalize(text: str | None) -> str:
    return _WHITESPACE.sub("", text or "")


def _contains_unnegated(normalized: str, stems: tuple[str, ...]) -> bool:
    """어간이 있고 바로 앞이 '안'/'못'이 아니며 바로 뒤가 '지않'이 아닌지."""
    for stem in stems:
        start = normalized.find(stem)
        while start != -1:
            before = normalized[:start]
            after = normalized[start + len(stem):]
            negated = before.endswith(("안", "못")) or after.startswith("지않")
            if not negated:
                return True
            start = normalized.find(stem, start + 1)
    return False


# ─────────────────────────────────────────────────────────────
# 거부
# ─────────────────────────────────────────────────────────────
# 오늘 미션 수행을 거부하는 표현만 잡습니다. "귀찮아" 단독은 1단계에서 기분 표현입니다.
REFUSAL_PHRASES: tuple[str, ...] = (
    "하기싫", "안할래", "안할거", "안할게", "그만할래", "나중에할래", "안나갈래", "안찍을래",
)
# 발화 전체가 이것뿐이면 거부로 봅니다. 문장 안에 섞이면 다른 뜻일 수 있어 단독일 때만.
REFUSAL_EXACT: frozenset[str] = frozenset({"싫어", "싫어요", "싫다", "안해", "안해요", "패스"})


def is_refusal(text: str | None) -> bool:
    normalized = _normalize(text).rstrip(".!?~…")
    if normalized in REFUSAL_EXACT:
        return True
    return any(p in normalized for p in REFUSAL_PHRASES)


# ─────────────────────────────────────────────────────────────
# 1단계 — 기분 텍스트
# ─────────────────────────────────────────────────────────────
# 긍정·부정·중립 모두 성공입니다. 특정 기분을 요구하면 강요가 됩니다.
MOOD_STEMS: tuple[str, ...] = (
    # 긍정
    "좋", "기쁘", "기뻐", "행복", "신나", "신났", "설레", "설렘", "편안", "편해", "괜찮", "상쾌",
    "뿌듯", "최고",
    # 부정
    "슬프", "슬퍼", "우울", "힘들", "힘드", "지치", "지쳐", "지쳤", "피곤", "짜증", "화나", "화났",
    "화가", "불안", "무섭", "무서", "외롭", "외로", "답답", "귀찮", "나쁘", "나빠", "별로",
    # 중립
    "그냥", "보통", "무난", "멍하", "멍해", "심심", "모르겠",
)


def has_mood_expression(text: str | None) -> bool:
    """기분 표현이 있는지. 부정문("안 좋아")도 기분을 말한 것이므로 인정합니다."""
    normalized = _normalize(text)
    return any(stem in normalized for stem in MOOD_STEMS)


def judge_mood(text: str | None) -> Judgement:
    if is_refusal(text):
        return Judgement(MissionResult.DEFERRED, None)
    if has_mood_expression(text):
        return Judgement(MissionResult.SUCCESS, ReasonCode.MOOD_OK)
    return Judgement(MissionResult.RETRY, ReasonCode.MOOD_NONE)


# ─────────────────────────────────────────────────────────────
# 2단계 — 날씨 음성 보고
# ─────────────────────────────────────────────────────────────
WEATHER_STEMS: dict[WeatherCategory, tuple[str, ...]] = {
    WeatherCategory.CLEAR: ("맑", "화창", "햇빛", "햇볕", "쨍", "해가", "해떴", "해났"),
    WeatherCategory.CLOUDS: ("흐리", "흐려", "흐림", "흐렸", "구름", "우중충"),
    WeatherCategory.RAIN: ("비와", "비가", "비오", "비내", "비도와", "비도오", "소나기", "빗방울", "우산"),
    # "눈이"는 "눈이 부셔"(햇빛)와 겹쳐서 넣지 않음
    WeatherCategory.SNOW: ("눈와", "눈오", "눈내", "눈이와", "눈이오", "눈이내", "함박눈", "눈발"),
    WeatherCategory.MIST: ("안개", "뿌옇", "뿌여", "미세먼지"),
}

# 관찰이 API와 조금 다른 것은 틀린 게 아닙니다. 대칭 관계로 둡니다.
_ADJACENT: frozenset[frozenset[WeatherCategory]] = frozenset(
    frozenset(pair)
    for pair in (
        (WeatherCategory.CLEAR, WeatherCategory.CLOUDS),
        (WeatherCategory.CLOUDS, WeatherCategory.RAIN),
        (WeatherCategory.CLOUDS, WeatherCategory.SNOW),
        (WeatherCategory.CLOUDS, WeatherCategory.MIST),
        (WeatherCategory.RAIN, WeatherCategory.SNOW),
    )
)


def is_adjacent(a: WeatherCategory, b: WeatherCategory) -> bool:
    return frozenset((a, b)) in _ADJACENT


def reported_weather(text: str | None) -> set[WeatherCategory]:
    """발화에서 보고된 날씨 범주. 부정("안 맑아", "비 안 와")은 제외합니다."""
    normalized = _normalize(text)
    return {cat for cat, stems in WEATHER_STEMS.items() if _contains_unnegated(normalized, stems)}


def judge_weather(
    text: str | None,
    stt_confidence: float | None,
    api_category: WeatherCategory | None,
) -> Judgement | None:
    """None이면 판정하지 않습니다 (STT 신뢰도 미달 → 예외 대화 5번으로 되묻기)."""
    if stt_confidence is not None and stt_confidence < STT_MIN_CONFIDENCE:
        return None
    if is_refusal(text):
        return Judgement(MissionResult.DEFERRED, None)

    reported = reported_weather(text)
    if not reported:
        return Judgement(MissionResult.RETRY, ReasonCode.WEATHER_NONE)
    if api_category is None:
        # 날씨 API 장애가 사용자 불이익이 되지 않게 합니다.
        return Judgement(MissionResult.SUCCESS, ReasonCode.WEATHER_API_DOWN)
    if api_category in reported:
        return Judgement(MissionResult.SUCCESS, ReasonCode.WEATHER_MATCH)
    if any(is_adjacent(api_category, r) for r in reported):
        return Judgement(MissionResult.SUCCESS, ReasonCode.WEATHER_NEAR)
    return Judgement(MissionResult.RETRY, ReasonCode.WEATHER_OPPOSITE)
