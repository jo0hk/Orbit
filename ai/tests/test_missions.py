"""미션 정의가 페르소나·HW 계약을 지키는지 검증.

이 테스트가 깨지면 대사나 신호가 1주차 확정안에서 벗어난 것입니다.
docs/mission-spec.md 를 먼저 확인하세요.
"""

import pytest

from app.missions import (
    BY_ID,
    MAX_SPEECH_LEN,
    MISSIONS,
    SIGNAL_DEFERRED,
    SIGNAL_SUCCESS,
    SIGNAL_TIMEOUT,
    MissionState,
)
from app.schemas import Led, OledExpression, Vibe

ALL_LINES = [
    (m.mission_id, kind, line)
    for m in MISSIONS
    for kind in ("propose", "success", "retry")
    for line in getattr(m, kind)
]


@pytest.mark.parametrize("mission_id,kind,line", ALL_LINES)
def test_speech_within_45_chars(mission_id, kind, line):
    """1학기 압축 규칙. 넘기면 레이턴시가 늘고 JSON이 깨질 위험이 커집니다."""
    assert len(line) <= MAX_SPEECH_LEN, f"{mission_id}.{kind}: {len(line)}자 — {line}"


@pytest.mark.parametrize("mission_id,kind,line", ALL_LINES)
def test_radio_protocol(mission_id, kind, line):
    """무전 프로토콜 — 치직- 으로 시작하고 통신 용어로 끝난다."""
    assert line.startswith("치직-"), f"{mission_id}.{kind}: 시작 표기 누락"
    assert line.rstrip().endswith(("오버", "라저", "교신 종료")), f"{mission_id}.{kind}: 종료 용어 누락"


@pytest.mark.parametrize("mission_id,kind", [(m.mission_id, k) for m in MISSIONS for k in ("propose", "success", "retry")])
def test_two_variants_exist(mission_id, kind):
    """같은 문장이 반복되면 몰입이 깨지므로 변형을 2종 이상 둔다."""
    lines = getattr(BY_ID[mission_id], kind)
    assert len(lines) >= 2
    assert len(set(lines)) == len(lines), f"{mission_id}.{kind}: 중복 대사"


def test_hw_signals_use_confirmed_enum():
    """1주차 확정 enum 밖의 값을 쓰면 HW가 해석할 수 없습니다."""
    for sig in (SIGNAL_SUCCESS, SIGNAL_TIMEOUT, SIGNAL_DEFERRED):
        assert isinstance(sig.led, Led)
        assert isinstance(sig.vibe, Vibe)
        assert isinstance(sig.oled, OledExpression)


def test_success_signal_is_celebratory():
    assert SIGNAL_SUCCESS.led is Led.RAINBOW
    assert SIGNAL_SUCCESS.oled is OledExpression.STAR_EYES


def test_timeout_signal_is_not_celebratory():
    """타임아웃에 축하 신호를 쓰면 압박으로 읽힙니다."""
    assert SIGNAL_TIMEOUT.led is not Led.RAINBOW
    assert SIGNAL_TIMEOUT.vibe is not Vibe.STRONG_DOUBLE


def test_no_failed_state():
    """FAILED 상태를 두지 않는다. 강요하는 서비스가 되기 때문."""
    assert "failed" not in {s.value for s in MissionState}


def test_stages_are_unique_and_ordered():
    stages = [m.stage for m in MISSIONS]
    assert stages == sorted(stages)
    assert len(set(stages)) == len(stages)


def test_fallback_targets_exist():
    """거부 시 제안할 대체 미션이 실제로 정의되어 있어야 합니다."""
    for m in MISSIONS:
        if m.fallback_mission_id:
            assert m.fallback_mission_id in BY_ID
            assert BY_ID[m.fallback_mission_id].active, f"{m.mission_id}의 대체 미션이 비활성"


def test_gps_mission_inactive_until_week7():
    assert BY_ID["m_gps_scout"].active is False
