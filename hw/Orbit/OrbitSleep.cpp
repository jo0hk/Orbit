#include "OrbitSleep.h"
#include "OrbitFace.h"
#include "OrbitLED.h"
#include "non_blocking_hw.h"
#include "mqtt_manager.h"

extern OrbitFace face;
extern OrbitLED orbit;

RTC_DATA_ATTR int bootCount = 0;

void initSleepSystem() {
  bootCount++;
  pinMode(SLEEP_TOUCH_PIN, INPUT_PULLDOWN);

  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  
  Serial.println("\n==============================================");
  Serial.printf("  오빗(Orbit) 시스템 구동 횟수: %d회\n", bootCount);
  Serial.println("==============================================");

  if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT0) {
    Serial.println("[Sleep] 터치 인터럽트에 의해 기상했습니다.");
  } else {
    Serial.println("[Sleep] 일반 전원 인가 및 하드웨어 리셋");
  }
}

void checkSleepTimer(unsigned long lastActivityTime) {
  if (millis() - lastActivityTime > SLEEP_TIMEOUT_MS) {
    Serial.println("\n[Sleep] 타임아웃 발생 -> 딥슬립 진입");
    enterOrbitDeepSleep();
  }
}

void enterOrbitDeepSleep() {
  Serial.println("[Sleep] 외부 터치 깨우기 인터럽트 설정 (GPIO 14)");
  esp_sleep_enable_ext0_wakeup(SLEEP_TOUCH_PIN, 1);

  // LED 및 진동 모터 안전 끄기
  stopLedEffect();
  orbit.showColor(0, 0, 0, 0);

  pinMode(VIBE_PIN, OUTPUT);
  digitalWrite(VIBE_PIN, LOW);

  Serial.flush();

  // MQTT 정상 종료 후 슬립
  shutdownMQTT();

  // OLED 자는 눈 애니메이션 후 패널 전원 끄기
  face.playSleepAnimation();

  esp_deep_sleep_start();
}