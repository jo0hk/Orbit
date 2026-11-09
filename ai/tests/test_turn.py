"""턴 단위 미션 판정과 기록 테스트.

흐름 규칙: docs/mission-context-injection.md 2-1절
"""

import asyncio

import pytest

from app.core.backend_client import BackendContext, TodayMission
from app.core.mission_judge import Judgement
from app.core.turn import MissionTurn, TurnRecord, judge_turn, persist_turn
from app.missions import BY_TYPE, Channel, MissionType, ReasonCode
from app.schemas import CommonEmotion, MissionResult
from tests.fakes import FAKE_MISSION, FAKE_MOOD_MISSION, FakeBackend, ok

S, R, D = MissionResult.SUCCESS, MissionResult.RETRY, MissionResult.DEFERRED


def ctx_with(mission: dict | None, weather: str | None = None) -> BackendContext:
    return BackendContext(
        user_id=3,
        mission=TodayMission.model_validate(mission) if mission else None,
        weather=weather,
    )


MOOD = ctx_with(FAKE_MOOD_MISSION)
WEATHER = ctx_with(FAKE_MISSION)


# ─── 판정 대상인지 ───────────────────────────────────────────
def test_no_mission_no_judgement():
    assert judge_turn(ctx_with(None), Channel.TEXT, "기분 좋아", None, high_risk=False) is None


def test_completed_mission_not_judged():
    """이미 완료한 미션은 다시 판정하지 않습니다 (칭찬 중복 방지)."""
    done = ctx_with({**FAKE_MOOD_MISSION, "status": "COMPLETED"})
    assert judge_turn(done, Channel.TEXT, "기분 좋아", None, high_risk=False) is None


def test_high_risk_not_judged():
    assert judge_turn(MOOD, Channel.TEXT, "기분 좋아", None, high_risk=True) is None


@pytest.mark.parametrize(
    "ctx, channel",
    [
        (MOOD, Channel.VOICE),    # 1단계는 앱 텍스트로만
        (WEATHER, Channel.TEXT),  # 2단계는 음성으로만
    ],
)
def test_channel_mismatch_not_judged(ctx, channel):
    assert judge_turn(ctx, channel, "맑아 기분 좋아", 0.9, high_risk=False) is None


def test_inactive_photo_mission_not_judged():
    photo = ctx_with({**FAKE_MISSION, "missionType": "LANDMARK_PHOTO", "stage": 3})
    assert judge_turn(photo, Channel.PHOTO, "사진", None, high_risk=False) is None


# ─── 1단계 기분 텍스트 ───────────────────────────────────────
@pytest.mark.parametrize(
    "text, result, reason",
    [
        ("오늘 좀 피곤해", S, ReasonCode.MOOD_OK),
        ("너무 우울해", S, ReasonCode.MOOD_OK),
        ("ㅇㅇ", R, ReasonCode.MOOD_NONE),
        ("하기 싫어", D, None),
    ],
)
def test_mood_mission(text, result, reason):
    turn = judge_turn(MOOD, Channel.TEXT, text, None, high_risk=False)

    assert turn.mission_id == 11
    assert turn.mission.mission_type is MissionType.EMOTION_TEXT
    assert turn.judgement.result is result
    assert turn.judgement.reason is reason


# ─── 2단계 날씨 음성 보고 ────────────────────────────────────
def test_weather_without_api_category_succeeds_on_expression():
    """백엔드에 날씨 API가 아직 없어 weather=None. 날씨 표현만 있으면 성공입니다."""
    turn = judge_turn(WEATHER, Channel.VOICE, "밖에 비가 와", 0.9, high_risk=False)

    assert turn.judgement.result is S
    assert turn.judgement.reason is ReasonCode.WEATHER_API_DOWN


def test_weather_with_api_category():
    ctx = ctx_with(FAKE_MISSION, weather="clear")  # 대소문자 무관
    turn = judge_turn(ctx, Channel.VOICE, "밖에 비가 와", 0.9, high_risk=False)

    assert turn.judgement.result is R
    assert turn.judgement.reason is ReasonCode.WEATHER_OPPOSITE


def test_weather_unknown_category_treated_as_missing():
    ctx = ctx_with(FAKE_MISSION, weather="태풍")
    turn = judge_turn(ctx, Channel.VOICE, "맑아", 0.9, high_risk=False)

    assert turn.judgement.reason is ReasonCode.WEATHER_API_DOWN


def test_low_stt_confidence_not_judged():
    assert judge_turn(WEATHER, Channel.VOICE, "맑아", 0.3, high_risk=False) is None


# ─── 기록 ────────────────────────────────────────────────────
def record(mission_turn=None, user_id=3) -> TurnRecord:
    return TurnRecord(
        user_id=user_id, request_id="req-1", channel=Channel.TEXT,
        user_text="오늘 좀 피곤해", orbit_speech="치직- 잘 받았습니다. 라저",
        emotion=CommonEmotion.CALM, stage=1, mission_turn=mission_turn,
    )


def mood_turn(result, reason) -> MissionTurn:
    return MissionTurn(11, BY_TYPE[MissionType.EMOTION_TEXT], Judgement(result, reason))


def persist(fake: FakeBackend, rec: TurnRecord):
    async def _main():
        client = fake.client()
        try:
            await persist_turn(client, rec)
        finally:
            await client.aclose()

    asyncio.run(_main())


def routes():
    return {
        ("POST", "/api/missions/11/result"): ok(FAKE_MOOD_MISSION),
        ("POST", "/api/conversations"): ok({}),
    }


def test_persist_reports_result_before_saving():
    fake = FakeBackend(routes())
    persist(fake, record(mood_turn(S, ReasonCode.MOOD_OK)))

    assert fake.paths() == [
        ("POST", "/api/missions/11/result"),
        ("POST", "/api/conversations"),
        ("POST", "/api/conversations"),
    ]
    rows = fake.bodies("POST", "/api/conversations")
    assert [r["channel"] for r in rows] == ["TEXT", "TEXT"]
    assert [r["stage"] for r in rows] == [1, 1]


def test_persist_deferred_saves_only_conversation():
    fake = FakeBackend(routes())
    persist(fake, record(mood_turn(D, None)))

    assert not fake.called("POST", "/api/missions/11/result")
    assert len(fake.bodies("POST", "/api/conversations")) == 2


def test_persist_without_mission_saves_only_conversation():
    fake = FakeBackend(routes())
    persist(fake, record())

    assert fake.paths() == [("POST", "/api/conversations")] * 2


def test_persist_unknown_user_does_nothing():
    fake = FakeBackend(routes())
    persist(fake, record(mood_turn(S, ReasonCode.MOOD_OK), user_id=None))

    assert fake.requests == []


def test_persist_without_backend_is_noop():
    asyncio.run(persist_turn(None, record()))
