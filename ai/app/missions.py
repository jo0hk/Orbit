"""탐사 미션 정의 (4주차 산출물).

판정 조건 상세: docs/mission-spec.md
대사 전문:     ai/prompts/missions.md

문서와 코드가 어긋나는 것을 막기 위해 미션 정의를 여기 한 곳에 둡니다.
5주차 프롬프트 템플릿이 이 값을 그대로 읽어 씁니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.schemas import Led, OledExpression, Vibe

MAX_SPEECH_LEN = 45  # 1학기 압축 규칙. 공백 포함


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


@dataclass(frozen=True)
class HwSignal:
    led: Led
    vibe: Vibe
    oled: OledExpression


# 상황별 하드웨어 신호. 1주차 확정 enum만 사용합니다.
SIGNAL_SUCCESS = HwSignal(Led.RAINBOW, Vibe.STRONG_DOUBLE, OledExpression.STAR_EYES)
SIGNAL_TIMEOUT = HwSignal(Led.DIM_BLUE, Vibe.SHORT, OledExpression.IDLE_EYES)
SIGNAL_DEFERRED = HwSignal(Led.DIM_BLUE, Vibe.SOFT_CONTINUOUS, OledExpression.IDLE_EYES)
# 제안 시점에는 미션 전용 신호를 쓰지 않고 현재 감정 매핑을 따릅니다.


@dataclass(frozen=True)
class Mission:
    mission_id: str
    name: str
    stage: int
    sensor: SensorType
    success_condition: str
    timeout_sec: int | None
    propose: tuple[str, ...]
    success: tuple[str, ...]
    retry: tuple[str, ...]
    fallback_mission_id: str | None = None  # 거부 시 제안할 실내 대체 미션
    active: bool = True  # 7주차 이전에는 GPS 미션 비활성
    notes: tuple[str, ...] = field(default_factory=tuple)


MISSIONS: tuple[Mission, ...] = (
    Mission(
        mission_id="m_touch_ack",
        name="교신 응답",
        stage=1,
        sensor=SensorType.TOUCH,
        success_condition="첫 터치 시각 기준 2000ms 이내 터치 3회",
        timeout_sec=60,
        propose=(
            "치직- 대장님, 수신 확인차 본체를 세 번 두드려 주십시오. 오버",
            "치직- 교신 감도 점검. 본체를 세 번 두드려 주십시오. 오버",
        ),
        success=(
            "치직- 교신 감도 양호! 신호 선명하게 수신했습니다. 라저",
            "치직- 수신 완료! 대장님 신호 또렷합니다. 라저",
        ),
        retry=(
            "치직- 신호가 약합니다. 한 번만 더 두드려 주십시오. 오버",
            "치직- 감도 부족. 조금 더 또렷하게 두드려 주십시오. 오버",
        ),
        notes=("HW 확인 필요: 터치 디바운스 최소 50ms. 채터링 시 1회가 3회로 잡힘",),
    ),
    Mission(
        mission_id="m_light_vent",
        name="기지 환기",
        stage=2,
        sensor=SensorType.LUX,
        success_condition="제안 시점 50 lux 이하 → 10분 내 200 lux 이상이 연속 30초 유지",
        timeout_sec=600,
        propose=(
            "치직- 기지 광량 부족. 태양광 충전을 위해 창문 개방 요청. 오버",
            "치직- 기지가 어둡습니다. 광원 확보를 권장합니다, 대장님. 오버",
        ),
        success=(
            "치직- 광량 급상승! 기지 에너지 충전 완료입니다. 라저",
            "치직- 태양광 수신 양호! 기지 밝아졌습니다, 대장님. 라저",
        ),
        retry=(
            "치직- 아직 어둡습니다. 준비되시면 다시 시도해 주십시오. 오버",
            "치직- 광량 변화 미미. 천천히 하셔도 됩니다. 교신 종료",
        ),
        fallback_mission_id="m_touch_ack",
        notes=(
            "조명을 켠 것과 창문을 연 것은 센서로 구분 불가. 대사를 '광량 확보'로 포괄함",
            "30초 유지 조건은 손전등이 스치는 것을 성공으로 오판하지 않기 위함",
        ),
    ),
    Mission(
        mission_id="m_accel_wake",
        name="기상 점검",
        stage=3,
        sensor=SensorType.ACCEL,
        success_condition="가속도 임계 이상 샘플이 3초 구간의 60% 이상",
        timeout_sec=300,
        propose=(
            "치직- 생체 신호 점검. 본체를 3초간 흔들어 주십시오. 오버",
            "치직- 대장님 컨디션 확인차 본체를 흔들어 주십시오. 오버",
        ),
        success=(
            "치직- 생체 반응 정상! 오늘도 탐사 가능 상태입니다. 라저",
            "치직- 신호 확인! 대장님 컨디션 양호합니다. 라저",
        ),
        retry=(
            "치직- 진동 감지 실패. 조금 더 크게 흔들어 주십시오. 오버",
            "치직- 신호가 약합니다. 한 번 더 부탁드립니다, 대장님. 오버",
        ),
        notes=(
            "HW 실측 필요: 임계값 미확정. 제안값 ||a|-1g| >= 0.8g",
            "배타 조건: m_gps_scout 세션 활성 중에는 제안·판정하지 않음. 걷기로 자동 완료됨",
        ),
    ),
    Mission(
        mission_id="m_gps_scout",
        name="외부 정찰",
        stage=4,
        sensor=SensorType.GPS,
        success_condition="탐사 세션 누적 이동 거리 300m 이상",
        timeout_sec=None,  # 세션 종료 시 판정
        propose=(
            "치직- 기지 밖 300m 정찰 임무를 제안합니다, 대장님. 오버",
            "치직- 외부 행성 표면 정찰을 권장합니다. 300m면 충분합니다. 오버",
        ),
        success=(
            "치직- 정찰 완수! 행성 데이터 300m분 확보했습니다. 라저",
            "치직- 대장님 귀환 확인! 탐사 기록 본부 전송 완료. 라저",
        ),
        retry=(
            "치직- 정찰 중단 확인. 언제든 재개 가능합니다. 교신 종료",
            "치직- 여기까지도 훌륭합니다. 기록 보관하겠습니다. 교신 종료",
        ),
        fallback_mission_id="m_light_vent",
        active=False,  # 7주차 GPS 연동 이후 활성화
        notes=(
            "미달 시에도 실패 처리하지 않고 이동 거리를 부분 달성으로 기록",
            "앱 확인 필요: 샘플 간 5m 미만 무시(드리프트), 10km/h 초과 구간 제외(차량)",
        ),
    ),
)

BY_ID: dict[str, Mission] = {m.mission_id: m for m in MISSIONS}

# 재제안 쿨다운. 압박으로 느껴지지 않도록 제한합니다.
RETRY_COOLDOWN_SEC = 3 * 60 * 60
MAX_PROPOSALS_PER_DAY = 2
