"""3단계 랜드마크 사진 판정 테스트 (11-13).

Gemini Vision 은 가짜로 바꾸고, 판독 결과 → 규칙 판정 → 대사·HW 신호 → 백엔드 기록을 확인합니다.
판정 규칙: docs/stage-mission-judgement.md 3단계
"""

import asyncio
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.interact import router
from app.core.mission_judge import judge_landmark
from app.core.pipeline import (
    PHOTO_LIMIT_SPEECH,
    PHOTO_PEOPLE_RETRY,
    PHOTO_PRAISE_DEFAULT,
    PHOTO_TRANSIT_NOT_READY,
    OrbitCore,
)
from app.core.vision import speech_follows_rules
from app.missions import BY_TYPE, Channel, MissionType, ReasonCode
from app.schemas import LandmarkReport, Led, MissionResult, OledExpression, Vibe
from tests.fakes import FAKE_MISSION, FakeBackend, ok

LANDMARK_MISSION = {**FAKE_MISSION, "missionId": 13, "stage": 3, "missionType": "LANDMARK_PHOTO"}
TRANSIT_MISSION = {**FAKE_MISSION, "missionId": 14, "stage": 4, "missionType": "TRANSIT"}
S, R = MissionResult.SUCCESS, MissionResult.RETRY

GOOD_SUCCESS = "치직- 붉은 벽돌 교회 관측 완료! 탐사 일지에 기록합니다. 라저"
GOOD_RETRY = "치직- 건물이 잘 안 보입니다. 원하시면 한 장 더 부탁드립니다. 오버"


def report(**kw) -> LandmarkReport:
    base = dict(
        is_outdoor=True, subject="building", people_prominent=False, confidence=0.82,
        description="붉은 벽돌 교회 건물", speech_success=GOOD_SUCCESS, speech_retry=GOOD_RETRY,
    )
    base.update(kw)
    return LandmarkReport(**base)


# ─── 규칙 판정 ───────────────────────────────────────────────
@pytest.mark.parametrize(
    "kw, result, reason",
    [
        ({}, S, ReasonCode.LANDMARK_OK),
        ({"subject": "sculpture"}, S, ReasonCode.LANDMARK_OK),
        ({"subject": "Signboard"}, S, ReasonCode.LANDMARK_OK),  # 대소문자 무관
        ({"confidence": 0.6}, S, ReasonCode.LANDMARK_OK),       # 경계값 포함
        ({"is_outdoor": False}, R, ReasonCode.LANDMARK_INDOOR),
        ({"subject": "other"}, R, ReasonCode.LANDMARK_SUBJECT),
        ({"confidence": 0.59}, R, ReasonCode.LANDMARK_LOW_CONF),
        ({"people_prominent": True}, R, ReasonCode.LANDMARK_PEOPLE),
        ({"subject": "person"}, R, ReasonCode.LANDMARK_PEOPLE),
        # 사람이 크게 찍혔으면 실내 여부보다 먼저 사람 안내 (얼굴 전송 방지)
        ({"people_prominent": True, "is_outdoor": False}, R, ReasonCode.LANDMARK_PEOPLE),
    ],
)
def test_judge_landmark(kw, result, reason):
    j = judge_landmark(report(**kw))
    assert j.result is result
    assert j.reason is reason


def test_judge_landmark_passes_confidence():
    assert judge_landmark(report(confidence=0.77)).confidence == 0.77


# ─── 대사 규칙 ───────────────────────────────────────────────
@pytest.mark.parametrize(
    "speech, retry, ok_",
    [
        (GOOD_SUCCESS, False, True),
        (GOOD_RETRY, True, True),
        ("치직- 좋습니다. 오버.", False, True),                       # 마침표 허용
        ("붉은 벽돌 교회 관측 완료. 라저", False, False),              # 치직 없음
        ("치직- " + "가" * 50 + " 오버", False, False),                # 45자 초과
        ("치직- 관측에 실패했습니다. 오버", False, False),             # 실패 금지
        ("치직- 건물이 안 보입니다", False, False),                    # 끝맺음 없음
        ("치직- 꼭 다시 찍어 주십시오. 오버", True, False),            # 재촉 금지
        ("", False, False),
    ],
)
def test_speech_rules(speech, retry, ok_):
    assert speech_follows_rules(speech, retry=retry) is ok_


# ─── 파이프라인 ──────────────────────────────────────────────
class FakeVision:
    def __init__(self, rep: LandmarkReport | None):
        self.rep, self.calls = rep, 0

    def inspect_landmark(self, image_path):
        self.calls += 1
        return self.rep


def routes(mission):
    r = {("POST", "/api/conversations"): ok({})}
    if mission:
        r[("GET", "/api/missions/current")] = ok(mission)
        r[("POST", f"/api/missions/{mission['missionId']}/result")] = ok(mission)
    return r


def make_core(fake, rep):
    core = OrbitCore(backend=fake.client())
    core.vision = FakeVision(rep)
    return core


def photo(core, **kw):
    return asyncio.run(core.interact_photo("dummy.jpg", user_id=1, **kw))


def test_landmark_success():
    fake = FakeBackend(routes(LANDMARK_MISSION))
    out = photo(make_core(fake, report()))
    res = out.response
    assert res.mission_result is S
    assert res.speech == GOOD_SUCCESS
    assert (res.led, res.vibe, res.oled_expression) == (Led.RAINBOW, Vibe.STRONG_DOUBLE, OledExpression.HAPPY)
    assert res.audio_url is None and res.next_step is None
    assert res.user_text == "[사진] 붉은 벽돌 교회 건물"
    rec = out.record
    assert rec.channel is Channel.PHOTO and rec.emotion is None
    assert rec.mission_turn.mission_id == 13
    assert rec.mission_turn.judgement.reason is ReasonCode.LANDMARK_OK


@pytest.mark.parametrize(
    "kw, expected",
    [
        ({"people_prominent": True}, PHOTO_PEOPLE_RETRY),
        ({"is_outdoor": False}, BY_TYPE[MissionType.LANDMARK_PHOTO].retry[0]),
        ({"subject": "other"}, GOOD_RETRY),
    ],
)
def test_landmark_retry_speech(kw, expected):
    res = photo(make_core(FakeBackend(routes(LANDMARK_MISSION)), report(**kw))).response
    assert res.mission_result is R
    assert res.speech == expected
    assert (res.led, res.vibe, res.oled_expression) == (Led.BLUE, Vibe.SHORT_PULSE, OledExpression.NORMAL)


def test_bad_gemini_speech_falls_back_to_written_lines():
    rep = report(speech_success="와 정말 멋진 교회네요 대장님!!")  # 치직·끝맺음 없음
    res = photo(make_core(FakeBackend(routes(LANDMARK_MISSION)), rep)).response
    assert res.speech == BY_TYPE[MissionType.LANDMARK_PHOTO].success[0]


def test_vision_failure_is_not_judged():
    fake = FakeBackend(routes(LANDMARK_MISSION))
    out = photo(make_core(fake, None))
    assert out.response.fallback_triggered
    assert out.response.mission_result is MissionResult.NONE
    assert out.record.mission_turn is None  # 결과 API 호출 안 함 → 다시 찍을 수 있음


def test_daily_limit():
    fake = FakeBackend(routes(LANDMARK_MISSION))
    core = make_core(fake, report(subject="other"))
    for _ in range(5):
        assert photo(core).response.mission_result is R
    out = photo(core)
    assert out.response.speech == PHOTO_LIMIT_SPEECH
    assert out.response.mission_result is MissionResult.NONE
    assert core.vision.calls == 5  # 6번째는 Gemini 를 부르지 않음


def test_no_photo_mission_only_praises():
    """사진 미션이 아닌 날(예: 1단계)에는 판정 없이 사진만 칭찬합니다."""
    mood = {**FAKE_MISSION, "missionId": 11, "stage": 1, "missionType": "EMOTION_TEXT"}
    out = photo(make_core(FakeBackend(routes(mood)), report()))
    assert out.response.mission_result is MissionResult.NONE
    assert out.response.speech == GOOD_SUCCESS
    assert out.record.mission_turn is None


def test_no_photo_mission_bad_praise_uses_default():
    out = photo(make_core(FakeBackend(routes(None)), report(speech_success="멋져요")))
    assert out.response.speech == PHOTO_PRAISE_DEFAULT


def test_transit_not_ready():
    fake = FakeBackend(routes(TRANSIT_MISSION))
    core = make_core(fake, report())
    out = photo(core)
    assert out.response.speech == PHOTO_TRANSIT_NOT_READY
    assert out.response.mission_result is MissionResult.NONE
    assert core.vision.calls == 0


def test_completed_landmark_not_judged_again():
    done = {**LANDMARK_MISSION, "status": "COMPLETED"}
    out = photo(make_core(FakeBackend(routes(done)), report()))
    assert out.response.mission_result is MissionResult.NONE
    assert out.record.mission_turn is None


# ─── 엔드포인트 ──────────────────────────────────────────────
def test_photo_endpoint_reports_result_and_saves(tmp_path):
    fake = FakeBackend(routes(LANDMARK_MISSION))
    app = FastAPI()
    app.include_router(router)
    app.state.backend = fake.client()
    app.state.core = make_core(fake, report())
    app.state.core.backend = app.state.backend
    client = TestClient(app)

    files = {"image": ("photo.jpg", io.BytesIO(b"\xff\xd8fakejpeg"), "image/jpeg")}
    data = {"user_id": "1", "captured_at": "2026-11-13T19:30:00+09:00", "request_id": "app-photo-1",
            "step": "", "lat": "37.5", "lng": "127.0"}
    resp = client.post("/api/v1/interact/photo", files=files, data=data)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mission_result"] == "success"
    assert body["next_step"] is None
    (result,) = fake.bodies("POST", "/api/missions/13/result")
    assert result["success"] is True and result["confidence"] == 0.82
    assert result["reason"] == "LANDMARK_OK"
    rows = fake.bodies("POST", "/api/conversations")
    assert [r["speaker"] for r in rows] == ["USER", "ORBIT"]
    assert rows[0]["message"] == "[사진] 붉은 벽돌 교회 건물"
    assert all(r["channel"] is None for r in rows)  # 백엔드 채널 enum 에 PHOTO 없음
    assert all(r["requestId"] == "app-photo-1" for r in rows)
    assert not any(str(v) in r["message"] for r in rows for v in ("37.5", "127.0"))  # 좌표 미저장


def test_photo_endpoint_requires_user_and_image():
    app = FastAPI()
    app.include_router(router)
    app.state.core = make_core(FakeBackend({}), report())
    client = TestClient(app)
    assert client.post("/api/v1/interact/photo", data={"user_id": "1"}).status_code == 422
    files = {"image": ("p.jpg", io.BytesIO(b"x"), "image/jpeg")}
    assert client.post("/api/v1/interact/photo", files=files).status_code == 422
