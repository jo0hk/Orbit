"""4단계 대중교통 판정 테스트 (11-20). 간단한 흐름 위주.

Gemini Vision 은 가짜로 바꿉니다. 기준값(5분·1km·촬영 1분 이내)은 OrbitCore 속성으로 조절합니다.
"""

import asyncio
from datetime import datetime, timedelta

from app.core.mission_judge import distance_km
from app.core.pipeline import (
    KST,
    TRANSIT_BOARDING_OK,
    TRANSIT_NEED_BOARDING,
    TRANSIT_STALE_PHOTO,
    OrbitCore,
)
from app.missions import ReasonCode
from app.schemas import MissionResult, TransitReport
from tests.fakes import FAKE_MISSION, FakeBackend, ok

TRANSIT = {**FAKE_MISSION, "missionId": 14, "stage": 4, "missionType": "TRANSIT"}
CITY_HALL = (37.5665, 126.9780)
SEOUL_STATION = (37.5547, 126.9707)  # 시청에서 약 1.46km


class FakeVision:
    def __init__(self):
        self.calls = []

    def inspect_transit(self, image_path, step):
        self.calls.append(step)
        return TransitReport(
            boarding_evidence=(step == "boarding"), stop_evidence=(step == "alighting"),
            people_prominent=False, confidence=0.9, description="교통카드 단말기",
            speech_success="치직- 은하 교통망 정복! 사회 궤도 진입입니다. 라저",
            speech_retry="치직- 역명판이 흐립니다. 한 장 더 부탁드립니다. 오버",
        )


def make_core(**limits):
    fake = FakeBackend({
        ("GET", "/api/missions/current"): ok(TRANSIT),
        ("POST", "/api/missions/14/result"): ok(TRANSIT),
        ("POST", "/api/conversations"): ok({}),
    })
    core = OrbitCore(backend=fake.client())
    core.vision = FakeVision()
    for k, v in limits.items():
        setattr(core, k, v)
    return core


def send(core, step, where, at=None):
    at = at or datetime.now(KST)
    return asyncio.run(core.interact_photo(
        "dummy.jpg", user_id=1, step=step, captured_at=at.isoformat(), lat=where[0], lng=where[1],
    ))


def test_distance():
    assert 1.4 < distance_km(*CITY_HALL, *SEOUL_STATION) < 1.5


def test_boarding_then_alighting_success():
    core = make_core(transit_min_minutes=0, transit_min_km=0)  # 실내 테스트 설정
    b = send(core, "boarding", CITY_HALL)
    assert b.response.speech == TRANSIT_BOARDING_OK
    assert b.response.next_step == "alighting"
    assert b.record.mission_turn is None  # 승차만으로는 결과 API 안 부름

    a = send(core, "alighting", CITY_HALL)
    assert a.response.mission_result is MissionResult.SUCCESS
    assert a.response.next_step is None
    assert a.record.mission_turn.judgement.reason is ReasonCode.TRANSIT_OK
    assert 1 not in core._boardings  # 성공하면 승차 기록(좌표) 삭제


def test_too_short_keeps_boarding():
    core = make_core()  # 실제 기준 5분 · 1km
    send(core, "boarding", CITY_HALL)
    a = send(core, "alighting", SEOUL_STATION)  # 거리는 충분하지만 바로 내림
    assert a.response.mission_result is MissionResult.RETRY
    assert a.record.mission_turn.judgement.reason is ReasonCode.TRANSIT_TIME
    assert a.response.next_step == "alighting"
    assert 1 in core._boardings  # 더 타고 가서 다시 찍을 수 있게 유지


def test_alighting_without_boarding():
    core = make_core()
    a = send(core, "alighting", CITY_HALL)
    assert a.response.speech == TRANSIT_NEED_BOARDING
    assert core.vision.calls == []


def test_stale_photo_rejected_before_gemini():
    core = make_core()
    old = datetime.now(KST) - timedelta(minutes=2)
    r = send(core, "boarding", CITY_HALL, at=old)
    assert r.response.speech == TRANSIT_STALE_PHOTO
    assert core.vision.calls == []  # 한도 절약
