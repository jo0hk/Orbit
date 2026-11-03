"""탐사 미션 정의 (10-01 교체).

09-17 회의에서 확정한 미션 구조를 코드로 옮긴 것입니다.
  - 단계 = 일일 미션. 단계당 미션 1개
  - AI 서버가 판정해 백엔드 결과 API로 보내고, 완료·단계 상승은 백엔드가 함

판정 조건:    docs/stage-mission-judgement.md
반응 문형:    docs/mission-context-injection.md 4절
대사 전문:    ai/prompts/missions.md
판정 함수:    app/core/mission_judge.py

4주차의 센서 미션 5개(터치·가속도·조도·GPS·자가 보고)는 회의 결정과 달라
교체했습니다. 기록은 docs/mission-spec.md 에 남아 있습니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.schemas import Led, OledExpression, Vibe

MAX_SPEECH_LEN = 45  # 1학기 압축 규칙. 공백 포함


class Stage(int, Enum):
    """기획안 4단계. 은둔 → 사회 복귀로 이어지는 서사 축입니다."""

    SYSTEM_CHECK = 1  # 시스템 점검 — 내 안의 작은 온기 확인
    AWAKENING = 2  # 감각의 깨움 — 외부 행성 주파수 수신
    SURFACE = 3  # 행성 표면 탐사 — 방 밖 미지의 행성 착륙
    CONTACT = 4  # 현지인과 교신 — 사회라는 은하로 복귀


class MissionType(str, Enum):
    """백엔드 MissionType enum과 같은 이름이어야 합니다 (Context API로 받음)."""

    EMOTION_TEXT = "EMOTION_TEXT"
    WEATHER_VOICE = "WEATHER_VOICE"
    LANDMARK_PHOTO = "LANDMARK_PHOTO"
    TRANSIT = "TRANSIT"


class Channel(str, Enum):
    """미션 수행 입력이 들어오는 경로. 다른 경로로 들어온 입력은 판정하지 않습니다."""

    TEXT = "TEXT"  # 앱 텍스트 교신
    VOICE = "VOICE"  # 키링 음성
    PHOTO = "PHOTO"  # 앱 카메라 촬영 (경로 미정)


class JudgeMethod(str, Enum):
    RULE = "RULE"  # 코드 규칙. LLM을 쓰지 않음
    VISION = "VISION"  # Gemini Vision 구조화 출력 + 규칙


class ReasonCode(str, Enum):
    """결과 API의 reason 코드. 로그·회귀 테스트용이며 사용자에게 보이지 않습니다."""

    MOOD_OK = "MOOD_OK"
    MOOD_NONE = "MOOD_NONE"
    WEATHER_MATCH = "WEATHER_MATCH"
    WEATHER_NEAR = "WEATHER_NEAR"
    WEATHER_OPPOSITE = "WEATHER_OPPOSITE"
    WEATHER_NONE = "WEATHER_NONE"
    WEATHER_API_DOWN = "WEATHER_API_DOWN"
    LANDMARK_OK = "LANDMARK_OK"
    LANDMARK_INDOOR = "LANDMARK_INDOOR"
    LANDMARK_SUBJECT = "LANDMARK_SUBJECT"
    LANDMARK_PEOPLE = "LANDMARK_PEOPLE"
    LANDMARK_LOW_CONF = "LANDMARK_LOW_CONF"
    TRANSIT_OK = "TRANSIT_OK"
    TRANSIT_TIME = "TRANSIT_TIME"
    TRANSIT_DISTANCE = "TRANSIT_DISTANCE"
    TRANSIT_PHOTO = "TRANSIT_PHOTO"


@dataclass(frozen=True)
class HwSignal:
    led: Led
    vibe: Vibe
    oled: OledExpression


# 공통 제어값 (docs/interface-spec-v1.md 3절, docs/mission-context-injection.md 1절)
SIGNAL_SUCCESS = HwSignal(Led.RAINBOW, Vibe.STRONG_DOUBLE, OledExpression.HAPPY)
SIGNAL_TIMEOUT = HwSignal(Led.BLUE, Vibe.SHORT_PULSE, OledExpression.NORMAL)  # 조건 미달
SIGNAL_DEFERRED = HwSignal(Led.BLUE, Vibe.SOFT_CONTINUOUS, OledExpression.NORMAL)  # 거부(보류)
# 제안 시점에는 미션 전용 신호를 쓰지 않고 현재 감정 매핑을 따릅니다.


@dataclass(frozen=True)
class Mission:
    stage: Stage
    mission_type: MissionType
    stage_name: str  # 기획안 단계 명칭
    title: str  # 기획안 미션 내용 그대로
    channel: Channel
    judge: JudgeMethod
    success_condition: str
    achievement: str  # 프롬프트 {achievement}
    shortfalls: dict[ReasonCode, str]  # 사유 코드 → 프롬프트 {shortfall}
    success_code: ReasonCode
    propose: tuple[str, ...]
    success: tuple[str, ...]
    retry: tuple[str, ...]
    daily_judge_limit: int | None = None  # Vision 판정 하루 상한 (Gemini 무료 한도)
    active: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)


MISSIONS: tuple[Mission, ...] = (
    Mission(
        stage=Stage.SYSTEM_CHECK,
        mission_type=MissionType.EMOTION_TEXT,
        stage_name="시스템 점검",
        title="앱 대화창에 오늘 기분 단어로 입력하기",
        channel=Channel.TEXT,
        judge=JudgeMethod.RULE,
        success_condition="기분 표현이 1개 이상. 어떤 기분이든 성공",
        achievement="오늘 기분을 말로 꺼내 보고했다",
        shortfalls={ReasonCode.MOOD_NONE: "기분을 나타내는 말이 잡히지 않음"},
        success_code=ReasonCode.MOOD_OK,
        propose=(
            "치직- 대장님, 오늘 기분을 한 단어로 송신해 주십시오. 오버",
            "치직- 시스템 점검 시간입니다. 지금 기분이 어떠십니까. 오버",
        ),
        success=(
            "치직- 본부에 긴급 타전! 대장님 첫 상태 보고 수신 완료. 라저",
            "치직- 기분 신호 수신! 교신 감도가 200% 올라갔습니다. 라저",
        ),
        retry=(
            "치직- 신호가 짧습니다. 지금 기분을 한 단어로 보내 주십시오. 오버",
            "치직- 기분 신호가 약합니다. 편하실 때 다시 송신 바랍니다. 오버",
        ),
        notes=(
            "감정 내용으로 성패를 가르지 않음. '우울해'도 성공",
            "'귀찮아' 단독은 거부가 아니라 기분으로 처리",
            "회의 표의 판정 주체는 '백엔드(AI 보조)'였으나 앱 텍스트가 AI 서버를 거치므로 AI 서버가 판정",
        ),
    ),
    Mission(
        stage=Stage.AWAKENING,
        mission_type=MissionType.WEATHER_VOICE,
        stage_name="감각의 깨움",
        title="창밖 날씨를 보고 오빗에게 음성으로 보고하기",
        channel=Channel.VOICE,
        judge=JudgeMethod.RULE,
        success_condition="날씨 표현 + 날씨 API 범주와 일치 또는 인접",
        achievement="창밖을 보고 날씨를 음성으로 보고했다",
        shortfalls={
            ReasonCode.WEATHER_OPPOSITE: "보고한 날씨가 기상 데이터와 정반대",
            ReasonCode.WEATHER_NONE: "날씨를 말하는 표현이 없음",
        },
        success_code=ReasonCode.WEATHER_MATCH,
        propose=(
            "치직- 대장님, 창밖 날씨를 관측해 음성으로 보고 바랍니다. 오버",
            "치직- 외부 행성 주파수 수신 시간. 오늘 하늘은 어떻습니까. 오버",
        ),
        success=(
            "치직- 은하 전역에 관측 보고 전파! 맑은 하늘 확인, 대장님. 라저",
            "치직- 창밖 관측 확인! 대장님 덕에 기상 데이터 확보입니다. 라저",
        ),
        retry=(
            "치직- 기상 센서와 다릅니다. 창밖을 한 번 더 봐 주시겠습니까. 오버",
            "치직- 날씨 정보가 안 잡힙니다. 하늘이 어떤지 알려 주십시오. 오버",
        ),
        notes=(
            "관찰을 API보다 우선. 인접 범주 허용, 정반대만 재시도",
            "날씨 API 장애 시 날씨 표현만 있으면 성공",
            "STT 신뢰도 0.5 미만이면 판정하지 않고 예외 대화 5번(되묻기)",
        ),
    ),
    Mission(
        stage=Stage.SURFACE,
        mission_type=MissionType.LANDMARK_PHOTO,
        stage_name="행성 표면 탐사",
        title="동네 랜드마크(건물, 조형물) 사진 찍기",
        channel=Channel.PHOTO,
        judge=JudgeMethod.VISION,
        success_condition="야외 사진, 피사체가 건물·조형물·간판, 신뢰도 0.6 이상",
        achievement="동네 랜드마크를 찍어 왔다",
        shortfalls={
            ReasonCode.LANDMARK_INDOOR: "실내로 판독됨",
            ReasonCode.LANDMARK_SUBJECT: "랜드마크가 또렷이 잡히지 않음",
            ReasonCode.LANDMARK_LOW_CONF: "랜드마크가 또렷이 잡히지 않음",
            ReasonCode.LANDMARK_PEOPLE: "사람이 주 피사체라 다시 찍어야 함",
        },
        success_code=ReasonCode.LANDMARK_OK,
        propose=(
            "치직- 동네 랜드마크를 찾아 사진으로 전송 바랍니다. 오버",
            "치직- 행성 표면 탐사 임무. 건물이나 조형물을 찍어 주십시오. 오버",
        ),
        success=(
            "치직- 탐사 일지에 첫 지형 기록! 대장님 덕에 지도가 넓어집니다. 라저",
            "치직- 행성 표면 사진 수신! 본부가 들썩입니다, 대장님. 라저",
        ),
        retry=(
            "치직- 실내로 판독됩니다. 바깥 풍경을 찍어 주시겠습니까. 오버",
            "치직- 랜드마크가 흐립니다. 건물이나 조형물을 다시 담아 주십시오. 오버",
        ),
        daily_judge_limit=5,
        active=False,  # 사진 업로드 경로(앱 → AI 서버) 확정 후 활성화
        notes=(
            "카메라 촬영만 허용(갤러리 불가). 사진 원본은 판정 후 저장하지 않음",
            "사람이 주 피사체면 사물을 찍도록 안내",
        ),
    ),
    Mission(
        stage=Stage.CONTACT,
        mission_type=MissionType.TRANSIT,
        stage_name="현지인과 교신",
        title="대중교통 이용해 세 정거장 이상 이동하기",
        channel=Channel.PHOTO,
        judge=JudgeMethod.VISION,
        success_condition="승차·하차 인증 사진 + 시간차 5분 이상 + 두 촬영 지점 직선거리 1km 이상",
        achievement="대중교통으로 세 정거장 이상 이동했다",
        shortfalls={
            ReasonCode.TRANSIT_TIME: "이동이 세 정거장에 못 미침",
            ReasonCode.TRANSIT_DISTANCE: "이동이 세 정거장에 못 미침",
            ReasonCode.TRANSIT_PHOTO: "인증 사진 판독 불가",
        },
        success_code=ReasonCode.TRANSIT_OK,
        propose=(
            "치직- 현지 교통망 탐사 임무. 세 정거장 이동을 제안합니다. 오버",
            "치직- 대장님, 버스나 지하철로 세 정거장 정찰 어떠십니까. 오버",
        ),
        success=(
            "치직- 은하 교통망 접속 성공! 대장님, 사회 궤도 진입입니다. 라저",
            "치직- 세 정거장 정찰 완수! 본부에 역사적 기록으로 남깁니다. 라저",
        ),
        retry=(
            "치직- 이동 거리가 조금 짧습니다. 다음에 이어 가셔도 좋습니다. 오버",
            "치직- 인증 사진 판독이 어렵습니다. 원하시면 다시 찍어 주십시오. 오버",
        ),
        daily_judge_limit=3,  # 승차·하차 각 3회
        active=False,  # 사진 업로드 경로 확정 후 활성화 (7~8주차 야외 테스트)
        notes=(
            "상시 마이크를 쓰지 않음. 승차(단말기·하차벨)와 하차(정류장·역명판)를 사물로 인증",
            "좌표는 거리 계산에만 쓰고 저장하지 않음",
        ),
    ),
)

BY_STAGE: dict[Stage, Mission] = {m.stage: m for m in MISSIONS}
BY_TYPE: dict[MissionType, Mission] = {m.mission_type: m for m in MISSIONS}
