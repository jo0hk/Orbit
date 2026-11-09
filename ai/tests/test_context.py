"""미션 반응 블록 주입 테스트.

템플릿 원문: docs/mission-context-injection.md 3절
"""

import pytest

from app.core.context import build_mission_block, build_system_prompt
from app.missions import BY_TYPE, MissionType, ReasonCode
from app.schemas import Emotion, EnvContext, MissionResult

MOOD = BY_TYPE[MissionType.EMOTION_TEXT]
WEATHER = BY_TYPE[MissionType.WEATHER_VOICE]


def env(result: MissionResult, mission_type=MissionType.EMOTION_TEXT, reason=None, **kw) -> EnvContext:
    return EnvContext(
        mission_id="11",
        mission_type=mission_type.value,
        mission_result=result,
        mission_reason=reason.value if reason else None,
        **kw,
    )


def test_no_mission_block_without_result():
    prompt = build_system_prompt(Emotion.NEUTRAL, EnvContext())
    assert "[미션 반응 수칙" not in prompt
    assert "미션 교신" not in prompt


def test_success_block():
    prompt = build_system_prompt(Emotion.NEUTRAL, env(MissionResult.SUCCESS))

    assert f"- 미션 교신: {MOOD.title} → 성공" in prompt
    assert "[미션 반응 수칙 — 임무 성공]" in prompt
    assert MOOD.achievement in prompt
    assert MOOD.success[0] in prompt and MOOD.success[1] in prompt
    assert "led는 rainbow, vibe는 strong_double" in prompt
    assert "가라앉아" not in prompt  # neutral 이면 온기 문장 없음


@pytest.mark.parametrize("emotion", [Emotion.SAD, Emotion.FEAR])
def test_success_softener_for_low_mood(emotion):
    block = build_mission_block(MOOD, env(MissionResult.SUCCESS), emotion)
    assert "과장 톤을 한 단계 낮춰" in block
    assert "축하 자체는 생략하지 마라" in block


def test_retry_block_uses_shortfall():
    e = env(MissionResult.RETRY, MissionType.WEATHER_VOICE, ReasonCode.WEATHER_OPPOSITE)
    prompt = build_system_prompt(Emotion.NEUTRAL, e)

    assert "조건 미달(재시도 가능)" in prompt
    assert "- 부족했던 것: 보고한 날씨가 기상 데이터와 정반대" in prompt
    assert WEATHER.retry[0] in prompt


def test_deferred_block():
    prompt = build_system_prompt(Emotion.NEUTRAL, env(MissionResult.DEFERRED))

    assert "[미션 반응 수칙 — 임무 보류]" in prompt
    assert "이 임무를 다시 권하지 마라" in prompt


def test_mission_turn_suppresses_environment_rules():
    """미션 반응 턴에는 조도·날씨 수칙을 끕니다 (3-4절)."""
    plain = build_system_prompt(Emotion.SAD, EnvContext(lux=10, weather="맑음"))
    assert "조도 제어" in plain and "날씨 제어" in plain

    mission = build_system_prompt(
        Emotion.SAD, env(MissionResult.SUCCESS, lux=10, weather="맑음")
    )
    assert "조도 제어" not in mission
    assert "날씨 제어" not in mission


@pytest.mark.parametrize("result", [MissionResult.SUCCESS, MissionResult.RETRY, MissionResult.DEFERRED])
@pytest.mark.parametrize("mission", [MOOD, WEATHER])
def test_block_length_budget(result, mission):
    """블록당 공백 포함 약 470자 이내 (조건부 문장 포함 최악값). 1학기 503 재발 방지."""
    reason = next(iter(mission.shortfalls)) if result is MissionResult.RETRY else None
    block = build_mission_block(mission, env(result, mission.mission_type, reason), Emotion.SAD)
    assert len(block) <= 470, len(block)


def test_unknown_mission_type_has_no_block():
    e = EnvContext(mission_type="NEW_TYPE", mission_result=MissionResult.SUCCESS)
    assert "[미션 반응 수칙" not in build_system_prompt(Emotion.NEUTRAL, e)
