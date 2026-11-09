"""백엔드 클라이언트 테스트.

실제 백엔드 없이 httpx.MockTransport로 백엔드 응답을 흉내 냅니다 (tests/fakes.py).
"""

import asyncio

import httpx
import pytest

from app.core.mission_judge import Judgement
from app.missions import Channel, MissionType, ReasonCode
from app.schemas import CommonEmotion, MissionResult
from tests.fakes import (
    FAKE_CHARACTER,
    FAKE_DEVICE,
    FAKE_MISSION,
    FAKE_RECENT,
    FakeBackend,
    ok,
)


def run(coro_factory, fake: FakeBackend):
    """클라이언트를 만들어 코루틴을 실행하고 닫습니다."""

    async def _main():
        client = fake.client()
        try:
            return await coro_factory(client)
        finally:
            await client.aclose()

    return asyncio.run(_main())


# ─── 맥락 조회 ───────────────────────────────────────────────
def test_fetch_context_by_device():
    fake = FakeBackend({
        ("GET", "/api/devices/ORBIT-001"): ok(FAKE_DEVICE),
        ("GET", "/api/character/7"): ok(FAKE_CHARACTER),
        ("GET", "/api/missions/current"): ok(FAKE_MISSION),
        ("GET", "/api/conversations/3/recent"): ok(FAKE_RECENT),
    })
    ctx = run(lambda c: c.fetch_context(device_id="ORBIT-001"), fake)

    assert ctx.user_id == 3
    assert ctx.char_id == 7
    assert ctx.stage == 2
    assert ctx.character.fuel == 45
    assert ctx.mission.mission_id == 12
    assert ctx.mission.mission_type is MissionType.WEATHER_VOICE
    assert ctx.mission.in_progress
    assert [t.speaker for t in ctx.recent] == ["USER", "ORBIT"]
    assert ctx.weather is None  # 백엔드에 날씨 제공 API 없음


def test_fetch_context_sends_user_id_query():
    fake = FakeBackend({
        ("GET", "/api/missions/current"): ok(FAKE_MISSION),
        ("GET", "/api/conversations/3/recent"): ok([]),
    })
    run(lambda c: c.fetch_context(user_id=3), fake)

    mission_req = next(r for r in fake.requests if r.url.path == "/api/missions/current")
    assert mission_req.url.params["userId"] == "3"
    recent_req = next(r for r in fake.requests if r.url.path.endswith("/recent"))
    assert recent_req.url.params["limit"] == "10"


def test_fetch_context_by_user_id_uses_mission_stage():
    """앱 텍스트는 user_id만 옵니다. 캐릭터를 userId로 찾는 API가 없어 미션 단계를 씁니다."""
    fake = FakeBackend({
        ("GET", "/api/missions/current"): ok(FAKE_MISSION),
        ("GET", "/api/conversations/3/recent"): ok([]),
    })
    ctx = run(lambda c: c.fetch_context(user_id=3), fake)

    assert ctx.character is None
    assert ctx.stage == 2
    assert not fake.called("GET", "/api/devices/ORBIT-001")


def test_unknown_device_falls_back_to_user_id():
    fake = FakeBackend({
        ("GET", "/api/missions/current"): ok(FAKE_MISSION),
        ("GET", "/api/conversations/3/recent"): ok([]),
    })  # 기기 조회는 404
    ctx = run(lambda c: c.fetch_context(device_id="ORBIT-999", user_id=3), fake)

    assert ctx.user_id == 3
    assert ctx.mission is not None


def test_unknown_device_without_user_returns_empty_context():
    fake = FakeBackend({})
    ctx = run(lambda c: c.fetch_context(device_id="ORBIT-999"), fake)

    assert ctx.user_id is None
    assert ctx.mission is None
    assert ctx.recent == []
    # 사용자를 모르면 미션·대화 조회를 하지 않음
    assert len(fake.requests) == 1


def test_backend_down_returns_empty_context():
    """백엔드가 꺼져 있어도 예외 없이 빈 맥락을 돌려줘야 합니다 (09-17 회의 원칙)."""
    fake = FakeBackend({
        ("GET", "/api/devices/ORBIT-001"): httpx.ConnectError("refused"),
    })
    ctx = run(lambda c: c.fetch_context(device_id="ORBIT-001"), fake)

    assert ctx.user_id is None
    assert ctx.stage is None


def test_timeout_on_mission_keeps_other_context():
    fake = FakeBackend({
        ("GET", "/api/devices/ORBIT-001"): ok(FAKE_DEVICE),
        ("GET", "/api/character/7"): ok(FAKE_CHARACTER),
        ("GET", "/api/missions/current"): httpx.ReadTimeout("slow"),
        ("POST", "/api/missions/today/assign"): httpx.ReadTimeout("slow"),
        ("GET", "/api/conversations/3/recent"): ok(FAKE_RECENT),
    })
    ctx = run(lambda c: c.fetch_context(device_id="ORBIT-001"), fake)

    assert ctx.mission is None
    assert ctx.stage == 2
    assert len(ctx.recent) == 2


# ─── 오늘 미션 ───────────────────────────────────────────────
def test_today_mission_assigns_when_missing():
    fake = FakeBackend({("POST", "/api/missions/today/assign"): ok(FAKE_MISSION)})
    mission = run(lambda c: c.get_today_mission(3), fake)

    assert mission.mission_id == 12
    assign_req = next(r for r in fake.requests if r.method == "POST")
    assert assign_req.url.params["userId"] == "3"


def test_today_mission_no_assign_when_disabled():
    fake = FakeBackend({("POST", "/api/missions/today/assign"): ok(FAKE_MISSION)})
    mission = run(lambda c: c.get_today_mission(3, assign_if_missing=False), fake)

    assert mission is None
    assert not fake.called("POST", "/api/missions/today/assign")


def test_completed_mission_is_not_in_progress():
    fake = FakeBackend({
        ("GET", "/api/missions/current"): ok({**FAKE_MISSION, "status": "COMPLETED"}),
    })
    mission = run(lambda c: c.get_today_mission(3), fake)

    assert not mission.in_progress


def test_unknown_mission_type_is_ignored():
    """백엔드에 AI가 모르는 미션 종류가 생기면 판정 대상에서 빼야 합니다."""
    fake = FakeBackend({
        ("GET", "/api/missions/current"): ok({**FAKE_MISSION, "missionType": "NEW_TYPE"}),
    })
    mission = run(lambda c: c.get_today_mission(3, assign_if_missing=False), fake)

    assert mission is None


def test_server_error_on_mission_returns_none():
    fake = FakeBackend({
        ("GET", "/api/missions/current"): httpx.Response(500, text="boom"),
        ("POST", "/api/missions/today/assign"): httpx.Response(500, text="boom"),
    })
    assert run(lambda c: c.get_today_mission(3), fake) is None


def test_recent_skips_malformed_rows():
    rows = [FAKE_RECENT[0], {"speaker": "USER"}]  # 두 번째는 message 없음
    fake = FakeBackend({("GET", "/api/conversations/3/recent"): ok(rows)})
    turns = run(lambda c: c.get_recent_conversations(3), fake)

    assert len(turns) == 1


def test_non_json_response_returns_none():
    fake = FakeBackend({("GET", "/api/devices/ORBIT-001"): httpx.Response(200, text="<html>")})
    assert run(lambda c: c.get_device("ORBIT-001"), fake) is None


# ─── 대화 저장 ───────────────────────────────────────────────
def save(client, **overrides):
    kwargs = dict(
        user_id=3, request_id="req-1", user_text="오늘 좀 피곤해",
        orbit_speech="치직- 대장님, 쉬어 가셔도 좋습니다. 오버",
        emotion=CommonEmotion.SAD, stage=2, channel=Channel.VOICE,
    )
    kwargs.update(overrides)
    return client.save_turn(**kwargs)


def test_save_turn_posts_user_and_orbit_rows():
    fake = FakeBackend({("POST", "/api/conversations"): ok({})})
    assert run(save, fake) is True

    user_row, orbit_row = fake.bodies("POST", "/api/conversations")
    assert user_row == {
        "userId": 3, "speaker": "USER", "message": "오늘 좀 피곤해",
        "emotion": "sad", "stage": 2, "channel": "VOICE", "requestId": "req-1",
    }
    assert orbit_row["speaker"] == "ORBIT"
    assert orbit_row["emotion"] is None  # emotion은 USER 행에만
    assert orbit_row["requestId"] == "req-1"  # 백엔드 중복 판정은 (requestId, speaker)


def test_save_turn_skips_empty_user_text():
    fake = FakeBackend({("POST", "/api/conversations"): ok({})})
    assert run(lambda c: save(c, user_text="  "), fake) is True

    rows = fake.bodies("POST", "/api/conversations")
    assert [r["speaker"] for r in rows] == ["ORBIT"]


def test_save_turn_photo_channel_sends_null():
    """백엔드 ConversationChannel은 TEXT·VOICE뿐이라 PHOTO는 null로 보냅니다."""
    fake = FakeBackend({("POST", "/api/conversations"): ok({})})
    run(lambda c: save(c, channel=Channel.PHOTO), fake)

    assert all(r["channel"] is None for r in fake.bodies("POST", "/api/conversations"))


def test_save_turn_failure_returns_false():
    fake = FakeBackend({("POST", "/api/conversations"): httpx.Response(409, text="필수")})
    assert run(save, fake) is False


def test_save_turn_backend_down_returns_false():
    fake = FakeBackend({("POST", "/api/conversations"): httpx.ConnectError("refused")})
    assert run(save, fake) is False


# ─── 미션 결과 ───────────────────────────────────────────────
def report(judgement, detail=None):
    return lambda c: c.report_mission_result(
        mission_id=12, user_id=3, judgement=judgement, detail=detail
    )


def test_success_posts_true():
    fake = FakeBackend({("POST", "/api/missions/12/result"): ok(FAKE_MISSION)})
    sent = run(report(Judgement(MissionResult.SUCCESS, ReasonCode.WEATHER_MATCH)), fake)

    assert sent is True
    (body,) = fake.bodies("POST", "/api/missions/12/result")
    assert body == {"userId": 3, "success": True, "confidence": 1.0, "reason": "WEATHER_MATCH"}


def test_retry_posts_false_with_detail():
    fake = FakeBackend({("POST", "/api/missions/12/result"): ok(FAKE_MISSION)})
    judgement = Judgement(MissionResult.RETRY, ReasonCode.WEATHER_OPPOSITE)
    sent = run(report(judgement, detail="맑음 보고, 기상 비"), fake)

    assert sent is True
    (body,) = fake.bodies("POST", "/api/missions/12/result")
    assert body["success"] is False
    assert body["reason"] == "WEATHER_OPPOSITE: 맑음 보고, 기상 비"


@pytest.mark.parametrize("result", [MissionResult.DEFERRED, MissionResult.NONE])
def test_deferred_and_none_do_not_call_backend(result):
    """거부(DEFERRED)는 결과 API를 호출하지 않습니다 (docs/stage-mission-judgement.md 3절)."""
    fake = FakeBackend({("POST", "/api/missions/12/result"): ok(FAKE_MISSION)})
    sent = run(report(Judgement(result, None)), fake)

    assert sent is None
    assert fake.requests == []


def test_already_completed_returns_false():
    fake = FakeBackend({("POST", "/api/missions/12/result"): httpx.Response(409, text="이미 완료")})
    sent = run(report(Judgement(MissionResult.SUCCESS, ReasonCode.MOOD_OK)), fake)

    assert sent is False


def test_result_backend_down_returns_false():
    fake = FakeBackend({("POST", "/api/missions/12/result"): httpx.ConnectTimeout("slow")})
    sent = run(report(Judgement(MissionResult.SUCCESS, ReasonCode.MOOD_OK)), fake)

    assert sent is False
