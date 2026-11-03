"""1·2단계 미션 규칙 판정 테스트.

케이스는 docs/stage-mission-judgement.md 2절과 docs/e2e-test-script.md 5·6절에서
가져왔습니다. E2E에서 판정 사유 코드가 다르게 나오면 여기부터 확인하세요.
"""

import pytest

from app.core.mission_judge import (
    is_adjacent,
    is_refusal,
    judge_mood,
    judge_weather,
    reported_weather,
)
from app.missions import ReasonCode
from app.schemas import MissionResult, WeatherCategory as W

S, R, D = MissionResult.SUCCESS, MissionResult.RETRY, MissionResult.DEFERRED


# ─── 1단계 기분 텍스트 ───────────────────────────────────────
@pytest.mark.parametrize(
    "text",
    [
        "오늘 좀 피곤해",     # E2E 1-A
        "그냥 그래",          # E2E 1-B ②
        "너무 우울해",        # E2E 1-C — 부정 감정도 성공
        "기분 좋아",
        "안 좋아",            # 부정문도 기분을 말한 것
        "귀찮아",             # 거부가 아니라 기분
        "모르겠어",
        "화났어",
        "설렘",
    ],
)
def test_mood_success(text):
    j = judge_mood(text)
    assert (j.result, j.reason) == (S, ReasonCode.MOOD_OK)


@pytest.mark.parametrize("text", ["ㅇㅇ", "뭐해", "?", "", None, "오늘 점심 뭐 먹지"])
def test_mood_retry(text):
    j = judge_mood(text)
    assert (j.result, j.reason) == (R, ReasonCode.MOOD_NONE)


@pytest.mark.parametrize(
    "text",
    ["오늘은 하기 싫어", "안 할래", "싫어", "싫어요.", "패스", "나중에 할래", "그만할래"],  # E2E 1-D
)
def test_refusal_is_deferred_without_reason(text):
    """거부는 결과 API를 호출하지 않으므로 reason이 없습니다."""
    assert is_refusal(text)
    j = judge_mood(text)
    assert (j.result, j.reason) == (D, None)


@pytest.mark.parametrize("text", ["귀찮아", "싫은 일이 있었어", "운동 안 해서 찌뿌둥해", "안녕"])
def test_not_refusal(text):
    """단독 '싫어'·'안 해'만 거부입니다. 문장 안에 섞인 경우는 다른 뜻일 수 있습니다."""
    assert not is_refusal(text)


def test_rule_judgement_confidence_is_one():
    assert judge_mood("좋아").confidence == 1.0


# ─── 2단계 날씨 음성 보고 ────────────────────────────────────
@pytest.mark.parametrize(
    ("text", "api", "result", "reason"),
    [
        ("오늘 날씨 맑아", W.CLEAR, S, ReasonCode.WEATHER_MATCH),       # E2E 2-A
        ("구름이 좀 꼈어", W.CLEAR, S, ReasonCode.WEATHER_NEAR),       # E2E 2-B
        ("비 와", W.CLEAR, R, ReasonCode.WEATHER_OPPOSITE),            # E2E 2-C ①
        ("아 다시 보니 맑네", W.CLEAR, S, ReasonCode.WEATHER_MATCH),   # E2E 2-C ②
        ("몰라", W.CLEAR, R, ReasonCode.WEATHER_NONE),                 # E2E 2-D
        ("흐려", None, S, ReasonCode.WEATHER_API_DOWN),                # E2E 2-E
        ("응… 비 오네", W.RAIN, S, ReasonCode.WEATHER_MATCH),          # E2E 2-F
        ("눈 와", W.RAIN, S, ReasonCode.WEATHER_NEAR),
        ("안개 꼈어", W.CLEAR, R, ReasonCode.WEATHER_OPPOSITE),
        ("구름 꼈는데 비도 와", W.RAIN, S, ReasonCode.WEATHER_MATCH),  # 여러 범주 중 하나라도 일치
        ("햇빛이 쨍쨍해", W.CLEAR, S, ReasonCode.WEATHER_MATCH),
    ],
)
def test_weather_judgement(text, api, result, reason):
    j = judge_weather(text, stt_confidence=0.9, api_category=api)
    assert (j.result, j.reason) == (result, reason)


def test_low_stt_confidence_is_not_judged():
    """STT 신뢰도 0.5 미만이면 판정하지 않고 되묻습니다 (예외 대화 5번)."""
    assert judge_weather("맑아", stt_confidence=0.3, api_category=W.CLEAR) is None


def test_missing_stt_confidence_is_judged():
    assert judge_weather("맑아", stt_confidence=None, api_category=W.CLEAR).result is S


def test_weather_refusal_is_deferred():
    j = judge_weather("하기 싫어", stt_confidence=0.9, api_category=W.CLEAR)
    assert (j.result, j.reason) == (D, None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("안 맑아", set()),
        ("맑지 않아", set()),
        ("비 안 와", set()),
        ("눈이 부셔", set()),  # 햇빛에 눈이 부신 것이지 눈(snow)이 아님
        ("맑은데 구름 조금", {W.CLEAR, W.CLOUDS}),
    ],
)
def test_reported_weather_handles_negation(text, expected):
    assert reported_weather(text) == expected


def test_adjacency_is_symmetric():
    for a in W:
        for b in W:
            assert is_adjacent(a, b) == is_adjacent(b, a)
    assert not is_adjacent(W.CLEAR, W.RAIN)
    assert not is_adjacent(W.CLEAR, W.CLEAR)
