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
    """WS2812B 네오픽셀 패턴. 값 출처: 1학기 ContextInjector 프롬프트."""

    RAINBOW = "rainbow"        # 긍정/중립, 환경 양호
    DIM_BLUE = "dim_blue"      # sad / fear, 또는 조도 50 lux 이하
    DIM_WHITE = "dim_white"    # anger / disgust
    ORANGE = "orange"          # 통신 장애 폴백


class Vibe(str, Enum):
    """PP-A811 진동 모터 패턴. 값 출처: 1학기 ContextInjector 프롬프트."""

    STRONG_DOUBLE = "strong_double"    # 긍정/중립
    SOFT_CONTINUOUS = "soft_continuous"  # sad / fear
    CALM_WAVE = "calm_wave"            # anger / disgust
    SHORT = "short"                    # 통신 장애 폴백
    NONE = "none"                      # 서버 전용. LLM은 선택하지 않음 (고위험 발화 대응)


class OledExpression(str, Enum):
    """OLED 픽셀 표정.

    ⚠️ 1학기 노트북에는 구현되어 있지 않습니다. LLM은 speech/led/vibe
       3종만 반환합니다. 아래 값은 페르소나 설정안(1주차 노션)에 적힌
       묘사를 코드로 옮긴 제안이며, HW 파트와 미합의 상태입니다.
    """

    IDLE_EYES = "idle_eyes"    # 평상시 동그란 픽셀 눈
    STAR_EYES = "star_eyes"    # 기쁠 때 반짝이는 별 모양
    SAD_EYES = "sad_eyes"
    WIDE_EYES = "wide_eyes"


def oled_for(emotion: Emotion) -> OledExpression:
    """감정 → 표정 매핑.

    TODO(1주차): HW 파트와 합의 후 확정하세요. LLM이 직접 반환하게 할지,
    서버에서 감정으로 파생할지도 결정 대상입니다. 현재는 파생 방식입니다.
    """
    return {
        Emotion.SAD: OledExpression.SAD_EYES,
        Emotion.FEAR: OledExpression.WIDE_EYES,
        Emotion.ANGER: OledExpression.WIDE_EYES,
        Emotion.DISGUST: OledExpression.WIDE_EYES,
        Emotion.NEUTRAL: OledExpression.IDLE_EYES,
    }.get(emotion, OledExpression.IDLE_EYES)


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
    oled_expression: OledExpression = OledExpression.IDLE_EYES

    audio_url: str | None = Field(None, description="무전 톤 합성이 끝난 음성 파일 경로")

    # --- 2주차 대화 로그 저장용 ---
    user_text: str = ""
    stt_confidence: float | None = None
    # "사용자의 감정". 백엔드 CharacterStatus.emotionStatus("오빗의 상태")와는
    # 다른 개념입니다. 1학기에 두 개념이 섞여 라벨 불일치가 발생했습니다.
    # 매핑 규칙은 docs/interface-spec-v1.md 2절 참조.
    user_emotion: Emotion = Emotion.NEUTRAL
    user_emotion_confidence: float | None = None

    # --- 운영 ---
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    llm_retry_count: int = 0
    fallback_triggered: bool = False

    # 고위험 발화 대응이 발동했는지. fallback_triggered(통신 장애)와 구분됩니다.
    # ⚠️ 통계 목적으로만 씁니다. 특정 사용자를 지목하거나 외부에 알리지 않습니다.
    #    docs/high-risk-utterance-policy.md 참조
    high_risk_detected: bool = False
