"""미션 정의가 09-17 회의 결정과 페르소나·HW 계약을 지키는지 검증.

이 테스트가 깨지면 미션 구조나 대사·신호가 확정안에서 벗어난 것입니다.
docs/stage-mission-judgement.md 를 먼저 확인하세요.
"""

import pytest

from app.missions import (
    BY_STAGE,
    BY_TYPE,
    MAX_SPEECH_LEN,
    MISSIONS,
    SIGNAL_DEFERRED,
    SIGNAL_SUCCESS,
    SIGNAL_TIMEOUT,
    Channel,
    JudgeMethod,
    MissionType,
    ReasonCode,
    Stage,
)
from app.schemas import Led, MissionResult, OledExpression, Vibe

ALL_LINES = [
    (m.mission_type.value, kind, line)
    for m in MISSIONS
    for kind in ("propose", "success", "retry")
    for line in getattr(m, kind)
]

# 재시도 대사 금지어 (docs/mission-context-injection.md 4-5)
RETRY_BANNED = ("빨리", "꼭", "반드시", "다시 해야", "왜")


def test_one_mission_per_stage():
    """09-17 회의: 단계 = 일일 미션. 단계당 미션 1개."""
    assert [int(m.stage) for m in MISSIONS] == [1, 2, 3, 4]
    assert set(BY_STAGE) == set(Stage)


def test_mission_types_match_backend_enum():
    """백엔드 MissionType과 이름이 같아야 Context API 값을 그대로 쓸 수 있습니다."""
    assert {t.value for t in MissionType} == {"EMOTION_TEXT", "WEATHER_VOICE", "LANDMARK_PHOTO", "TRANSIT"}
    assert set(BY_TYPE) == set(MissionType)


def test_missions_follow_planned_scenario():
    """기획안 4단계 탐사 시나리오(노션 메인 페이지)와 순서가 같아야 합니다."""
    assert [m.mission_type for m in MISSIONS] == [
        MissionType.EMOTION_TEXT,
        MissionType.WEATHER_VOICE,
        MissionType.LANDMARK_PHOTO,
        MissionType.TRANSIT,
    ]


@pytest.mark.parametrize("mission_type,kind,line", ALL_LINES)
def test_speech_within_45_chars(mission_type, kind, line):
    """1학기 압축 규칙. 넘기면 레이턴시가 늘고 JSON이 깨질 위험이 커집니다."""
    assert len(line) <= MAX_SPEECH_LEN, f"{mission_type}.{kind}: {len(line)}자 — {line}"


@pytest.mark.parametrize("mission_type,kind,line", ALL_LINES)
def test_radio_protocol(mission_type, kind, line):
    """무전 프로토콜 — 치직- 으로 시작하고 통신 용어로 끝난다."""
    assert line.startswith("치직-"), f"{mission_type}.{kind}: 시작 표기 누락"
    assert line.rstrip().endswith(("오버", "라저", "교신 종료")), f"{mission_type}.{kind}: 종료 용어 누락"


@pytest.mark.parametrize("mission_type,kind,line", ALL_LINES)
def test_no_failure_word(mission_type, kind, line):
    """'실패'라는 단어를 쓰지 않습니다. 조건 미달은 실패가 아니라 '아직'입니다."""
    assert "실패" not in line


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.mission_type.value)
def test_retry_lines_do_not_pressure(mission):
    for line in mission.retry:
        assert not any(word in line for word in RETRY_BANNED), line


@pytest.mark.parametrize(
    "mission_type,kind", [(m.mission_type.value, k) for m in MISSIONS for k in ("propose", "success", "retry")]
)
def test_two_variants_exist(mission_type, kind):
    """같은 문장이 반복되면 몰입이 깨지므로 변형을 2종 이상 둔다."""
    lines = getattr(BY_TYPE[MissionType(mission_type)], kind)
    assert len(lines) >= 2
    assert len(set(lines)) == len(lines), f"{mission_type}.{kind}: 중복 대사"


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda m: m.mission_type.value)
def test_reason_codes_belong_to_mission(mission):
    """성공 코드와 미달 코드가 미션 종류와 맞는지 (예: 1단계에 WEATHER_* 가 섞이지 않게)."""
    prefix = {
        MissionType.EMOTION_TEXT: "MOOD_",
        MissionType.WEATHER_VOICE: "WEATHER_",
        MissionType.LANDMARK_PHOTO: "LANDMARK_",
        MissionType.TRANSIT: "TRANSIT_",
    }[mission.mission_type]
    assert mission.success_code.value.startswith(prefix)
    assert mission.shortfalls
    for code, text in mission.shortfalls.items():
        assert code.value.startswith(prefix)
        assert code is not mission.success_code
        assert text.strip()


def test_every_reason_code_is_used():
    used = {m.success_code for m in MISSIONS} | {c for m in MISSIONS for c in m.shortfalls}
    # 성공으로 끝나는 보조 코드는 shortfalls에 없음
    used |= {ReasonCode.WEATHER_NEAR, ReasonCode.WEATHER_API_DOWN}
    assert used == set(ReasonCode)


def test_hw_signals_use_confirmed_enum():
    for sig in (SIGNAL_SUCCESS, SIGNAL_TIMEOUT, SIGNAL_DEFERRED):
        assert isinstance(sig.led, Led)
        assert isinstance(sig.vibe, Vibe)
        assert isinstance(sig.oled, OledExpression)


def test_success_signal_is_celebratory():
    assert SIGNAL_SUCCESS.led is Led.RAINBOW
    assert SIGNAL_SUCCESS.oled is OledExpression.HAPPY


def test_retry_and_deferred_are_not_celebratory_and_differ():
    """조건 미달에 축하 신호를 쓰면 압박으로 읽힙니다. 미달과 보류는 진동으로 구분됩니다."""
    for sig in (SIGNAL_TIMEOUT, SIGNAL_DEFERRED):
        assert sig.led is not Led.RAINBOW
        assert sig.vibe is not Vibe.STRONG_DOUBLE
    assert SIGNAL_TIMEOUT.vibe is not SIGNAL_DEFERRED.vibe


def test_no_failed_result():
    """FAILED를 두지 않는다. 강요하는 서비스가 되기 때문."""
    assert {r.value for r in MissionResult} == {"success", "retry", "deferred", "none"}


def test_channels_and_judges():
    assert BY_STAGE[Stage.SYSTEM_CHECK].channel is Channel.TEXT
    assert BY_STAGE[Stage.AWAKENING].channel is Channel.VOICE
    for stage in (Stage.SYSTEM_CHECK, Stage.AWAKENING):
        assert BY_STAGE[stage].judge is JudgeMethod.RULE
    for stage in (Stage.SURFACE, Stage.CONTACT):
        assert BY_STAGE[stage].judge is JudgeMethod.VISION
        assert BY_STAGE[stage].daily_judge_limit, "Vision 판정은 Gemini 무료 한도 때문에 하루 상한이 필요"


def test_photo_missions_inactive_until_upload_path():
    """사진 업로드 경로(앱 → AI 서버)가 정해지기 전에는 판정할 수 없습니다."""
    assert BY_STAGE[Stage.SYSTEM_CHECK].active
    assert BY_STAGE[Stage.AWAKENING].active
    assert not BY_STAGE[Stage.SURFACE].active
    assert not BY_STAGE[Stage.CONTACT].active


def test_contact_stage_does_not_use_always_on_mic():
    """4단계는 상시 마이크로 타인과의 대화를 듣지 않습니다. 사물 사진으로 인증합니다."""
    assert BY_STAGE[Stage.CONTACT].channel is not Channel.VOICE
