#ifndef NON_BLOCKING_HW_H
#define NON_BLOCKING_HW_H

#include <Arduino.h>
#include "OrbitLED.h"

#define VIBE_PIN 12

enum LedEffectState {
  LED_IDLE,    // 평상시: 현재 Stage 색상 지속 유지 (숨쉬기)
  LED_BREATH,  // 지정된 R,G,B 색상으로 일시적 숨쉬기 연출
  LED_FADE     // 지정된 R,G,B 색상으로 일시적 페이드 연출
};

enum VibePatternState {
  VIBE_IDLE,
  VIBE_SHORT,
  VIBE_LONG,
  VIBE_DOUBLE
};

void setupNonBlockingHW(OrbitLED* ledPtr);
void updateNonBlockingHW();


// 지정 색상(r, g, b)으로 일시적 효과를 주는 트리거 API
void triggerBreathEffect(uint8_t r = 135, uint8_t g = 206, uint8_t b = 250, uint16_t duration_ms = 3000);
void triggerFadeEffect(uint8_t r = 135, uint8_t g = 206, uint8_t b = 250, uint16_t duration_ms = 1000);
void triggerVibration(VibePatternState pattern);
void stopLedEffect();

#endif