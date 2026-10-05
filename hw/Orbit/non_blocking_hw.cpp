#include "non_blocking_hw.h"
#include "stage_manager.h"

static OrbitLED* globalLed = nullptr;

static LedEffectState currentLedState = LED_IDLE;
static unsigned long ledEffectStartTime = 0;
static uint16_t ledEffectDuration = 0;

static uint8_t effectR = 0, effectG = 0, effectB = 0;

static VibePatternState currentVibeState = VIBE_IDLE;
static unsigned long vibeStartTime = 0;
static uint8_t vibeStep = 0;

void setupNonBlockingHW(OrbitLED* ledPtr) {
  globalLed = ledPtr;
  pinMode(VIBE_PIN, OUTPUT);
  digitalWrite(VIBE_PIN, LOW);
}

static void updateLED() {
  if (globalLed == nullptr) return;

  unsigned long now = millis();

  if (currentLedState != LED_BREATH && currentLedState != LED_FADE) {
    // 1. 평상시 (LED_IDLE): Stage 대표색 숨쉬기
    StageColor curColor = getCurrentStageColor();
    unsigned long cycle = now % 3000;
    uint8_t baseBrightness = (cycle < 1500) ? map(cycle, 0, 1500, 10, 40) 
                                            : map(cycle - 1500, 0, 1500, 40, 10);
    globalLed->showColor(curColor.r, curColor.g, curColor.b, baseBrightness);
    return;
  }

  // 2. 일시적 LED 효과 (BREATH / FADE)
  unsigned long elapsed = now - ledEffectStartTime;

  if (currentLedState == LED_BREATH) {
    // ★ 원본 원복: % 연산으로 손을 대고 있는 동안 노란빛 페이드 무한 유지
    uint16_t halfDuration = ledEffectDuration / 2;
    unsigned long progress = elapsed % ledEffectDuration; 

    uint8_t brightness = 0;
    if (progress < halfDuration) {
      brightness = map(progress, 0, halfDuration, 10, 100);
    } else {
      brightness = map(progress - halfDuration, 0, halfDuration, 100, 10);
    }

    globalLed->showColor(effectR, effectG, effectB, brightness);
  } 
  else if (currentLedState == LED_FADE) {
    if (elapsed >= ledEffectDuration) {
      currentLedState = LED_IDLE; // Fade 효과는 시간 종료 시 스테이지 대표색으로 복귀
      return;
    }
    uint8_t brightness = map(elapsed, 0, ledEffectDuration, 10, 150);
    globalLed->showColor(effectR, effectG, effectB, brightness);
  }
}

static void updateVibration() {
  if (currentVibeState == VIBE_IDLE) return;

  unsigned long elapsed = millis() - vibeStartTime;

  switch (currentVibeState) {
    case VIBE_SHORT:
      if (elapsed < 100) digitalWrite(VIBE_PIN, HIGH);
      else { digitalWrite(VIBE_PIN, LOW); currentVibeState = VIBE_IDLE; }
      break;

    case VIBE_LONG:
      if (elapsed < 500) digitalWrite(VIBE_PIN, HIGH);
      else { digitalWrite(VIBE_PIN, LOW); currentVibeState = VIBE_IDLE; }
      break;

    case VIBE_DOUBLE:
      if (vibeStep == 0) {
        digitalWrite(VIBE_PIN, HIGH);
        if (elapsed >= 100) { vibeStep = 1; vibeStartTime = millis(); }
      } else if (vibeStep == 1) {
        digitalWrite(VIBE_PIN, LOW);
        if (elapsed >= 100) { vibeStep = 2; vibeStartTime = millis(); }
      } else if (vibeStep == 2) {
        digitalWrite(VIBE_PIN, HIGH);
        if (elapsed >= 100) {
          digitalWrite(VIBE_PIN, LOW);
          currentVibeState = VIBE_IDLE;
        }
      }
      break;

    default:
      digitalWrite(VIBE_PIN, LOW);
      currentVibeState = VIBE_IDLE;
      break;
  }
}

void updateNonBlockingHW() {
  updateLED();
  updateVibration();
}

void triggerBreathEffect(uint8_t r, uint8_t g, uint8_t b, uint16_t duration_ms) {
  currentLedState = LED_BREATH;
  effectR = r; effectG = g; effectB = b;
  ledEffectStartTime = millis();
  ledEffectDuration = duration_ms;
}

void triggerFadeEffect(uint8_t r, uint8_t g, uint8_t b, uint16_t duration_ms) {
  currentLedState = LED_FADE;
  effectR = r; effectG = g; effectB = b;
  ledEffectStartTime = millis();
  ledEffectDuration = duration_ms;
}

void triggerVibration(VibePatternState pattern) {
  currentVibeState = pattern;
  vibeStartTime = millis();
  vibeStep = 0;
}

void stopLedEffect() {
  currentLedState = LED_IDLE;
}