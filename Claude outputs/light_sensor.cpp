#include "light_sensor.h"
#include "config.h"
#include <Arduino.h>

// GL5528 계열 추정값 (실측 보정 필요)
#define LDR_R_AT_10LUX  15000.0f
#define LDR_GAMMA       0.7f
#define SAMPLE_COUNT    16

void lightBegin() {
  analogReadResolution(12);
  analogSetPinAttenuation(LIGHT_PIN, ADC_11db);
}

int lightReadLux() {
  uint32_t sum = 0;
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    sum += analogReadMilliVolts(LIGHT_PIN);
    delayMicroseconds(200);
  }
  int mv = sum / SAMPLE_COUNT;
  if (mv <= 10 || mv >= 3290) return -1;   // 0 나누기·포화 방지

  float r = LIGHT_R_FIXED_OHM * (3300.0f / mv - 1.0f);
  int lux = (int)(10.0f * powf(LDR_R_AT_10LUX / r, 1.0f / LDR_GAMMA));
  Serial.printf("[Light] %d mV -> 약 %d lux\n", mv, lux);
  return lux;
}
