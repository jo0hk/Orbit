#ifndef NON_BLOCKING_HW_H
#define NON_BLOCKING_HW_H

#include <Arduino.h>
#include "OrbitLED.h"

#define VIBE_PIN 12

enum LedEffectState {
  LED_IDLE,
  LED_BREATH,
  LED_FADE
};

enum VibePatternState {
  VIBE_IDLE,
  VIBE_SHORT,
  VIBE_LONG,
  VIBE_DOUBLE
};

void setupNonBlockingHW(OrbitLED* ledPtr);
void updateNonBlockingHW();

void triggerBreathEffect(uint8_t r = 135, uint8_t g = 206, uint8_t b = 250, uint16_t duration_ms = 3000);
void triggerFadeEffect(uint8_t r = 135, uint8_t g = 206, uint8_t b = 250, uint16_t duration_ms = 1000);
void triggerVibration(VibePatternState pattern);
void stopLedEffect();

#endif