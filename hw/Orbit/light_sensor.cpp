#include "light_sensor.h"
#include "config.h"
#include <Arduino.h>
#include <driver/adc.h>      // 예전 방식 ADC: I2S 예전 드라이버와 충돌 방지
#include <esp_adc_cal.h>

#if LIGHT_PIN != 34
#error "LIGHT_PIN을 바꾸면 아래 LIGHT_ADC_CH도 맞춰야 함 (GPIO34 = ADC1_CHANNEL_6)"
#endif
#define LIGHT_ADC_CH    ADC1_CHANNEL_6

// GL5528 계열 추정값 (실측 보정 필요)
#define LDR_R_AT_10LUX  15000.0f
#define LDR_GAMMA       0.7f
#define SAMPLE_COUNT    16

static esp_adc_cal_characteristics_t adcChars;
static bool adcReady = false;

void lightBegin() {
  if (adc1_config_width(ADC_WIDTH_BIT_12) != ESP_OK ||
      adc1_config_channel_atten(LIGHT_ADC_CH, ADC_ATTEN_DB_12) != ESP_OK) {
    Serial.println("[Light] ADC 설정 실패");
    return;
  }
  esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_12, ADC_WIDTH_BIT_12, 1100, &adcChars);
  adcReady = true;
}

int lightReadLux() {
  if (!adcReady) return -1;
  uint32_t sum = 0;
  int valid = 0;
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    int raw = adc1_get_raw(LIGHT_ADC_CH);
    if (raw >= 0) { sum += raw; valid++; }
    delayMicroseconds(200);
  }
  if (valid == 0) return -1;

  int mv = esp_adc_cal_raw_to_voltage(sum / valid, &adcChars);
  if (mv <= 10 || mv >= 3290) return -1;   // 0 나누기·포화 방지

  float r = LIGHT_R_FIXED_OHM * (3300.0f / mv - 1.0f);
  int lux = (int)(10.0f * powf(LDR_R_AT_10LUX / r, 1.0f / LDR_GAMMA));
  Serial.printf("[Light] %d mV -> 약 %d lux\n", mv, lux);
  return lux;
}