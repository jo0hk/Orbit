"""요청/응답 스키마 및 파트 간 공유 enum.

⚠️ 이 파일의 enum은 1주차 "인터페이스 정의서 v1"의 코드판입니다.
   값은 1학기 Colab 노트북(Orbit.ipynb)의 ContextInjector 프롬프트에
   실제로 박혀 있던 것을 그대로 옮긴 것입니다. 추측값이 아닙니다.
   HW/앱과 합의 없이 값을 추가하면 파트 간 불일치가 다시 발생합니다.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# 감정 라벨
# ─────────────────────────────────────────────────────────────
class Emotion(str, Enum):
    """3주차 멀티모달 감정 분류 모델의 출력 클래스.

    ⚠️ 실제 라벨은 체크포인트의 checkpoint['label_encoder']에서 옵니다.
       EmotionEngine이 로딩 시 이 enum과 일치하는지 검증하고,
       다르면 기동을 중단합니다(조용한 불일치 방지).

    ⚠️ 1주차 결정 사항: 5클래스가 전부 부정/중립이라 미션 성공 칭찬을
       감정 엔진이 받쳐주지 못합니다. HAPPY 추가 재학습 여부를 정하세요.
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
    """WS2812B 네오픽셀. AI가 보내는 이벤트 색입니다.

    LED 공통 제어값(10-01 확정, docs/interface-spec-v1.md 3절)은 색깔 영어명입니다.
    AI는 이 중 rainbow / blue 만 보냅니다. purple·yellow는 HW 내부 반응,
    pink·orange·lime·green은 HW가 평상시 켜는 1~4단계 테마색입니다.
    이벤트 색은 잠깐 켜진 뒤 단계 테마색으로 돌아갑니다.

    ⚠️ HW applyHardwareAction 은 아직 "dim_blue" 라는 이름으로만 파랑을 받습니다.
       HW가 "blue" 분기를 추가할 때까지 파랑 신호는 표시되지 않습니다.
    """

    RAINBOW = "rainbow"  # 긍정/중립, 미션 성공. 색 이름은 아니지만 축하 연출이라 예외로 둠
    BLUE = "blue"        # sad / fear / anger / disgust, 조도 50 lux 이하, 미션 미달·보류, 비상·고위험


class Vibe(str, Enum):
    """PP-A811 진동 모터 패턴. 09-17 공통 진동값 중 HW 구현분."""

    STRONG_DOUBLE = "strong_double"      # 긍정/중립, 미션 성공
    SOFT_CONTINUOUS = "soft_continuous"  # sad / fear, 미션 보류
    SHORT_PULSE = "short_pulse"          # anger / disgust, 미션 조건 미달, 비상
    NONE = "none"                        # 서버 전용. LLM은 선택하지 않음 (고위험 발화 대응)
    # calm_wave, two_short_taps 는 공통값에 있으나 HW 미구현. 구현되면 추가합니다.


class OledExpression(str, Enum):
    """OLED 픽셀 표정. 09-17 공통 제어값(EXPR_*) 중 AI 서버가 쓰는 것.

    LLM은 반환하지 않고 서버가 감정·상황에서 파생합니다.
    ⚠️ EXPR_HAPPY 는 HW applyHardwareAction 에 분기가 아직 없습니다 (HW 작업).
    """

    NORMAL = "EXPR_NORMAL"        # 평상시
    HAPPY = "EXPR_HAPPY"          # 미션 성공, Vision 칭찬
    SAD = "EXPR_SAD"              # sad / fear, 비상·고위험
    LISTENING = "EXPR_LISTENING"  # 다시 말해 달라고 할 때 (무응답, STT 실패)
    THINKING = "EXPR_THINKING"    # 처리 중


def oled_for(emotion: Emotion) -> OledExpression:
    """감정 → 표정 매핑. 서버에서 감정으로 파생합니다.

    anger / disgust 는 표정을 바꾸지 않습니다. 적대 발화에 오빗이 흔들리지
    않는다는 예외 대화 3번 원칙과 같습니다.
    """
    return {
        Emotion.SAD: OledExpression.SAD,
        Emotion.FEAR: OledExpression.SAD,
        Emotion.ANGER: OledExpression.NORMAL,
        Emotion.DISGUST: OledExpression.NORMAL,
        Emotion.NEUTRAL: OledExpression.NORMAL,
    }.get(emotion, OledExpression.NORMAL)


class CommonEmotion(str, Enum):
    """09-17 회의에서 확정한 공통 감정값. 백엔드·앱이 쓰는 값입니다.

    감정 모델 출력(Emotion)을 이 값으로 바꾸는 규칙은
    app/core/emotion_map.py 와 docs/interface-spec-v1.md 2절에 있습니다.
    백엔드 Emotion enum이 이 4개만 받으므로 대화 저장에는 반드시 이 값을 씁니다.
    """

    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    CALM = "calm"


class MissionResult(str, Enum):
    """AI 서버의 미션 판정 결과. Context Injector에 주입됩니다.

    FAILED(실패)는 두지 않습니다. 조건 미달은 RETRY(같은 날 다시 할 수 있음),
    거부는 DEFERRED(보류, 결과 API를 호출하지 않음)입니다.
    docs/mission-context-injection.md 1절, docs/stage-mission-judgement.md 3절
    """

    SUCCESS = "success"    # 백엔드 결과 API success:true
    RETRY = "retry"        # 백엔드 결과 API success:false
    DEFERRED = "deferred"  # 거부. 결과 API 호출 안 함
    NONE = "none"          # 미션과 무관한 턴


class WeatherCategory(str, Enum):
    """2단계 미션 판정용 날씨 범주. 백엔드 Context API가 이 값으로 줍니다 (요청 사항).

    docs/stage-mission-judgement.md 2절
    """

    CLEAR = "CLEAR"    # 맑음
    CLOUDS = "CLOUDS"  # 흐림
    RAIN = "RAIN"      # 비
    SNOW = "SNOW"      # 눈
    MIST = "MIST"      # 안개


# ─────────────────────────────────────────────────────────────
# 요청
# ─────────────────────────────────────────────────────────────
class EnvContext(BaseModel):
    """Context Injector 입력. HW/앱에서 전달됩니다.

    ⚠️ 1학기에는 전부 하드코딩된 가상값이었습니다(weather="화창함",
       illuminance=15). 실제 센서 연동 여부를 1주차에 확인하세요.
    """

    lux: int | None = Field(None, description="조도. 50 이하면 환기 권유 로직 동작")
    weather: str | None = Field(None, description="예: 화창함, 맑음, 비")
    location_coarse: str | None = Field(None, description="비식별 위치. 좌표 원본 금지")
    distance_m: int | None = Field(None, description="7주차 GPS 누적 이동 거리")
    mission_id: str | None = None
    mission_result: MissionResult = MissionResult.NONE


# ─────────────────────────────────────────────────────────────
# 응답
# ─────────────────────────────────────────────────────────────
class LatencyBreakdown(BaseModel):
    """2주차 스키마의 latency_ms. 단계별로 남겨야 병목을 찾을 수 있습니다.

    ⚠️ 기준선 없음. 1학기 "6초대"는 Gemini 호출이 실패한 상태에서
       tenacity 백오프 대기 시간을 잰 값이라 유효하지 않습니다.
       1주차에 정상 응답 기준으로 다시 측정하세요.
    """

    stt_ms: int = 0
    emotion_ms: int = 0
    llm_ms: int = 0
    tts_ms: int = 0
    total_ms: int = 0


class InteractResponse(BaseModel):
    """LLM이 Strict JSON으로 반환하는 구조 + 운영 메타데이터.

    speech / led / vibe 3종이 1학기에 확립된 계약입니다.
    oled_expression은 서버에서 감정으로 파생합니다(LLM 미반환).
    """

    speech: str
    led: Led
    vibe: Vibe
    oled_expression: OledExpression = OledExpression.NORMAL

    audio_url: str | None = Field(None, description="무전 톤 합성이 끝난 음성 파일 경로")

    # --- 2주차 대화 로그 저장용 ---
    user_text: str = ""
    stt_confidence: float | None = None
    # "사용자의 감정". 백엔드 CharacterStatus.emotionStatus("오빗의 상태")와는
    # 다른 개념입니다. 1학기에 두 개념이 섞여 라벨 불일치가 발생했습니다.
    # 매핑 규칙은 docs/interface-spec-v1.md 2절 참조.
    user_emotion: Emotion = Emotion.NEUTRAL
    user_emotion_confidence: float | None = None
    # user_emotion을 공통 감정값으로 바꾼 것. 앱·백엔드는 이 값을 씁니다.
    # user_emotion(원래 라벨)은 고위험 2차 탐지와 오분류 수집용으로 남깁니다.
    emotion: CommonEmotion = CommonEmotion.CALM

    # --- 운영 ---
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    llm_retry_count: int = 0
    fallback_triggered: bool = False

    # 고위험 발화 대응이 발동했는지. fallback_triggered(통신 장애)와 구분됩니다.
    # ⚠️ 통계 목적으로만 씁니다. 특정 사용자를 지목하거나 외부에 알리지 않습니다.
    #    docs/high-risk-utterance-policy.md 참조
    high_risk_detected: bool = False
