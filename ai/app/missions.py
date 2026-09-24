"""탐사 미션 정의 (4주차 산출물).

원본:         docs/reference/mission-list-1st-semester.md (80개 미션 / 4단계)
판정 조건:    docs/mission-spec.md
대사 전문:    ai/prompts/missions.md

원본 80개 중 **현재 하드웨어로 판정 가능한 5개**를 골라 구현 대상으로 삼습니다.
단계 구성과 미션 명칭은 원본을 그대로 따릅니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.schemas import Led, OledExpression, Vibe

MAX_SPEECH_LEN = 45  # 1학기 압축 규칙. 공백 포함


class Stage(int, Enum):
    """원본 4단계. 은둔 → 사회 복귀로 이어지는 서사 축입니다."""

    SYSTEM_CHECK = 1  # 시스템 점검 — 방 안, 자기 돌봄
    AWAKENING = 2  # 감각의 깨움 — 창을 열고 경계 확장
    SURFACE = 3  # 행성 표면 탐사 — 실제 외출과 산책
    CONTACT = 4  # 현지인과 교신 — 사회 복귀


class MissionState(str, Enum):
    """⚠️ FAILED를 두지 않습니다.

    조건 미달은 TIMEOUT(유예) 또는 DEFERRED(보류)로만 기록합니다.
    실패 판정은 3주차 예외 대화의 '강요하지 않는다' 원칙과 충돌합니다.
    """

    PROPOSED = "proposed"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    DEFERRED = "deferred"


class SensorType(str, Enum):
    """MQTT 미션 판정 채널의 payload.type."""

    TOUCH = "TOUCH"
    LUX = "LUX"
    ACCEL = "ACCEL"
    GPS = "GPS"
    SELF_REPORT = "SELF_REPORT"  # 앱 미션 완료 버튼. 센서 판정 불가한 미션용


@dataclass(frozen=True)
class HwSignal:
    led: Led
    vibe: Vibe
    oled: OledExpression


SIGNAL_SUCCESS = HwSignal(Led.RAINBOW, Vibe.STRONG_DOUBLE, OledExpression.STAR_EYES)
SIGNAL_TIMEOUT = HwSignal(Led.DIM_BLUE, Vibe.SHORT, OledExpression.IDLE_EYES)
SIGNAL_DEFERRED = HwSignal(Led.DIM_BLUE, Vibe.SOFT_CONTINUOUS, OledExpression.IDLE_EYES)
# 제안 시점에는 미션 전용 신호를 쓰지 않고 현재 감정 매핑을 따릅니다.


@dataclass(frozen=True)
class Mission:
    mission_id: str
    name: str  # 원본 미션 명칭을 그대로 사용
    stage: Stage
    sensor: SensorType
    success_condition: str
    timeout_sec: int | None
    propose: tuple[str, ...]
    success: tuple[str, ...]
    retry: tuple[str, ...]
    origin_verification: str  # 원본 '검증 방법' 원문
    fallback_mission_id: str | None = None  # 거부 시 제안할 대체 미션
    active: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)


MISSIONS: tuple[Mission, ...] = (
    Mission(
        mission_id="m_warm_touch",
        name="아침 온기 나누기",
        stage=Stage.SYSTEM_CHECK,
        sensor=SensorType.TOUCH,
        success_condition="터치 신호가 3초 이상 연속 유지",
        timeout_sec=120,
        origin_verification="터치 센서가 3초 이상 연속 신호 감지",
        propose=(
            "치직- 대장님, 키링을 손바닥으로 3초간 감싸 쥐어 주십시오. 오버",
            "치직- 온기 수신 대기 중. 3초간 감싸 쥐어 주십시오, 대장님. 오버",
        ),
        success=(
            "치직- 대장님의 온기 수신 완료. 회로가 예열됐습니다. 라저",
            "치직- 온기 확인! 오늘 하루도 무사히 착륙해 봐요, 대장님. 라저",
        ),
        retry=(
            "치직- 온기 신호가 끊겼습니다. 조금 더 오래 쥐어 주십시오. 오버",
            "치직- 수신 미완. 천천히 다시 시도하셔도 됩니다. 교신 종료",
        ),
        notes=(
            "원본 1단계 첫 미션. 연속 유지 판정이라 3회 카운트보다 오탐이 적음",
            "HW 확인: 손에 쥔 상태의 정전용량 변화가 3초간 안정적으로 잡히는지",
        ),
    ),
    Mission(
        mission_id="m_engine_start",
        name="엔진 시동 인사",
        stage=Stage.SYSTEM_CHECK,
        sensor=SensorType.ACCEL,
        success_condition="짧고 강한 충격 2회 (간격 300~1500ms)",
        timeout_sec=300,
        origin_verification="가속도 센서가 짧고 강한 충격 2회 감지",
        propose=(
            "치직- 대장님, 제 머리를 두 번 톡톡 두드려 깨워 주십시오. 오버",
            "치직- 엔진 시동 대기 중. 두 번 두드려 주십시오, 대장님. 오버",
        ),
        success=(
            "치직- 대장님 응답 확인! 엔진 가동 준비 완료됐습니다. 오버",
            "치직- 시동 성공! 오늘의 미션을 하달해 주시겠습니까. 라저",
        ),
        retry=(
            "치직- 충격 감지 실패. 조금 더 또렷하게 두드려 주십시오. 오버",
            "치직- 신호가 약합니다. 한 번 더 부탁드립니다, 대장님. 오버",
        ),
        notes=(
            "원본은 '두드려 깨우기'. 흔들기(궤도 회전 테스트)와 달리 충격 패턴이라 걷기와 구분이 쉬움",
            "HW 실측 필요: 충격 임계값과 2회 간격 범위",
        ),
    ),
    Mission(
        mission_id="m_solar_panel",
        name="태양광 패널 전면 개방",
        stage=Stage.AWAKENING,
        sensor=SensorType.LUX,
        success_condition="제안 시점 50 lux 이하 → 10분 내 200 lux 이상이 연속 30초 유지",
        timeout_sec=600,
        origin_verification="조도 센서가 낮은 수치에서 급격히 상승하여 일정 시간 유지",
        propose=(
            "치직- 기지 광량 부족. 커튼을 열어 패널을 개방해 주십시오. 오버",
            "치직- 태양 에너지 수신 대기 중. 창을 열어 주십시오, 대장님. 오버",
        ),
        success=(
            "치직- 태양 에너지 쏟아집니다! 기지 밝기 최적화 완료. 라저",
            "치직- 광량 급상승! 기분이 한결 환해지네요, 대장님. 라저",
        ),
        retry=(
            "치직- 아직 어둡습니다. 준비되시면 다시 시도해 주십시오. 오버",
            "치직- 광량 변화 미미. 천천히 하셔도 됩니다. 교신 종료",
        ),
        fallback_mission_id="m_warm_touch",
        notes=(
            "원본의 '일정 시간 유지'를 30초로 구체화. 손전등이 스치는 것을 오판하지 않기 위함",
            "커튼을 연 것과 전등을 켠 것은 센서로 구분 불가. 원본 1단계 '태양광 패널 점검'(전등)과 사실상 같은 판정",
        ),
    ),
    Mission(
        mission_id="m_basecamp_100m",
        name="베이스캠프 반경 확보",
        stage=Stage.SURFACE,
        sensor=SensorType.GPS,
        success_condition="집 출발 후 누적 이동 거리 100m 이상",
        timeout_sec=None,  # 세션 종료 시 판정
        origin_verification="핸드폰 GPS 기반 이동 거리 측정 (실시간 지도 트래킹)",
        propose=(
            "치직- 베이스캠프 반경 100m 확보 임무를 제안합니다. 오버",
            "치직- 기지 밖 100m 지점까지 정찰을 권장합니다, 대장님. 오버",
        ),
        success=(
            "치직- 베이스캠프 주변 안전 확인 완료. 대기 질 양호합니다. 라저",
            "치직- 정찰 완수! 조금 더 깊이 탐사해 볼까요, 대장님. 라저",
        ),
        retry=(
            "치직- 정찰 중단 확인. 언제든 재개 가능합니다. 교신 종료",
            "치직- 여기까지도 훌륭합니다. 기록 보관하겠습니다. 교신 종료",
        ),
        fallback_mission_id="m_solar_panel",
        active=False,  # 7주차 GPS 연동 이후 활성화
        notes=(
            "원본 거리는 100m. 300m는 근거 없는 상향이었음",
            "앱 확인 필요: 샘플 간 5m 미만 무시(드리프트), 10km/h 초과 구간 제외(차량)",
            "100m는 GPS 오차(±10m)와 가까우므로 드리프트 필터가 특히 중요",
        ),
    ),
    Mission(
        mission_id="m_first_greeting",
        name="첫 번째 외교적 수사",
        stage=Stage.CONTACT,
        sensor=SensorType.SELF_REPORT,
        success_condition="앱에서 사용자가 완료 보고",
        timeout_sec=None,
        origin_verification="마이크 센서 및 STT로 인사말 키워드 추출",
        propose=(
            "치직- 현지인에게 인사 교신을 시도해 보시겠습니까, 대장님. 오버",
            "치직- 외교 임무 제안. 점원에게 인사 한마디 어떠십니까. 오버",
        ),
        success=(
            "치직- 현지인과 첫 교신 성공! 목소리 주파수 당당했습니다. 라저",
            "치직- 외교적 첫걸음 확인! 대장님, 아주 훌륭했습니다. 라저",
        ),
        retry=(
            "치직- 다음 기회에 시도해도 좋습니다. 서두르지 마십시오. 교신 종료",
            "치직- 접수. 준비되셨을 때 다시 보고해 주십시오. 교신 종료",
        ),
        fallback_mission_id="m_solar_panel",
        active=False,  # 앱 미션 완료 버튼 구현 필요
        notes=(
            "⚠️ 원본 검증 방법(상시 마이크 + STT)은 채택하지 않음. 타인과의 대화를 상시 청취해야 하므로 "
            "본인과 상대방 모두의 개인정보 문제가 발생함",
            "자가 보고로 대체. 4단계 서사를 유지하면서 프라이버시 문제를 피하는 유일한 방법",
        ),
    ),
)

BY_ID: dict[str, Mission] = {m.mission_id: m for m in MISSIONS}

# 재제안 쿨다운. 압박으로 느껴지지 않도록 제한합니다.
RETRY_COOLDOWN_SEC = 3 * 60 * 60
MAX_PROPOSALS_PER_DAY = 2
