"""요청/응답 스키마 및 파트 간 공유 enum.

⚠️ 이 파일의 enum은 1주차 "인터페이스 정의서 v1"의 코드판입니다.
   HW/앱/백엔드와 합의한 값만 여기에 존재해야 하며,
   합의 없이 값을 추가하면 파트 간 불일치가 다시 발생합니다.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# 감정 라벨
# ─────────────────────────────────────────────────────────────
class Emotion(str, Enum):
    """3주차 멀티모달 감정 분류 모델의 출력 클래스.

    ⚠️ 1주차 결정 사항: 현재 5클래스가 전부 부정/중립이라
       미션 성공 칭찬을 감정 엔진이 받쳐주지 못합니다.
       HAPPY 추가 재학습 여부를 결정한 뒤 이 enum을 확정하세요.
    """

    SAD = "sad"
    ANGER = "anger"
    FEAR = "fear"
    DISGUST = "disgust"
    NEUTRAL = "neutral"
    # HAPPY = "happy"  # TODO(1주차): 재학습 결정 시 활성화


# ─────────────────────────────────────────────────────────────
# 하드웨어 제어 신호
# ─────────────────────────────────────────────────────────────
class Led(str, Enum):
    """WS2812B 네오픽셀 패턴. TODO(1주차): HW 파트와 값 확정."""

    DIM_BLUE = "dim_blue"            # 1학기 실사용: 위로/안정
    ORANGE_PULSE = "orange_pulse"    # 1학기 실사용: 통신 두절 비상
    GREEN_SPARKLE = "green_sparkle"  # 제안: 미션 성공
    WARM_YELLOW = "warm_yellow"      # 제안: 광량 확보
    RAINBOW_SWEEP = "rainbow_sweep"  # 제안: 탐사 완수


class Vibe(str, Enum):
    """PP-A811 진동 모터 패턴. TODO(1주차): HW 파트와 값 확정."""

    NONE = "none"
    TWO_SHORT_TAPS = "two_short_taps"      # 1학기 실사용: 불안/경고
    SOFT_CONTINUOUS = "soft_continuous"    # 1학기 실사용: 위로
    DOUBLE_BUZZ = "double_buzz"            # 제안: 확인
    CELEBRATION = "celebration_pattern"    # 제안: 미션 완수


class OledExpression(str, Enum):
    """OLED 픽셀 표정. TODO(1주차): HW 파트와 값 확정."""

    IDLE_EYES = "idle_eyes"      # 평상시 동그란 눈
    STAR_EYES = "star_eyes"      # 기쁨
    HAPPY_EYES = "happy_eyes"
    WIDE_EYES = "wide_eyes"
    SAD_EYES = "sad_eyes"


class MissionResult(str, Enum):
    """5주차: 미션 판정 결과. Context Injector에 주입됩니다."""

    SUCCESS = "success"
    FAIL = "fail"
    RETRY = "retry"
    NONE = "none"


# ─────────────────────────────────────────────────────────────
# 요청
# ─────────────────────────────────────────────────────────────
class EnvContext(BaseModel):
    """4주차 Context Injector 입력. HW/앱에서 전달됩니다.

    ⚠️ 1학기에는 전부 가상값이었습니다. 실제 센서 연동 여부를 1주차에 확인하세요.
    """

    lux: int | None = Field(None, description="조도 센서값. 50 이하면 환기 권유 로직 동작")
    weather: str | None = Field(None, description="예: 화창함, 비")
    location_coarse: str | None = Field(None, description="비식별 위치. 좌표 원본 금지")
    distance_m: int | None = Field(None, description="7주차 GPS 누적 이동 거리")
    mission_id: str | None = None
    mission_result: MissionResult = MissionResult.NONE


class InteractRequest(BaseModel):
    session_id: str
    turn_no: int
    context: EnvContext = Field(default_factory=EnvContext)


# ─────────────────────────────────────────────────────────────
# 응답
# ─────────────────────────────────────────────────────────────
class LatencyBreakdown(BaseModel):
    """2주차 스키마의 latency_ms. 단계별로 남겨야 병목을 찾을 수 있습니다.

    1학기 기준선: 전체 6초대 (최초 10.51초에서 단축).
    미션 판정이 붙는 5주차 이후 이 값이 다시 늘어나는지 감시하세요.
    """

    stt_ms: int = 0
    emotion_ms: int = 0
    llm_ms: int = 0
    tts_ms: int = 0
    total_ms: int = 0


class InteractResponse(BaseModel):
    """LLM이 Strict JSON으로 반환하는 구조 + 운영 메타데이터.

    speech / led / vibe 3종은 1학기에 확립한 계약입니다.
    oled_expression은 5주차 HW 매핑표에서 추가되었습니다.
    """

    speech: str
    led: Led
    vibe: Vibe
    oled_expression: OledExpression = OledExpression.IDLE_EYES

    audio_url: str | None = Field(None, description="무전 톤 합성이 끝난 음성 파일 경로")

    # --- 2주차 대화 로그 저장용 ---
    user_text: str = ""
    stt_confidence: float | None = None
    emotion: Emotion = Emotion.NEUTRAL
    emotion_confidence: float | None = None

    # --- 운영 ---
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    llm_retry_count: int = 0
    fallback_triggered: bool = False
