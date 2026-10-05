#include "OrbitSleep.h"
#include "OrbitFace.h"
#include "OrbitLED.h"
#include "non_blocking_hw.h" // stopLedEffect() 및 VIBE_PIN 정의 포함

extern OrbitFace face;
extern OrbitLED orbit; // Orbit.ino에 정의된 전역 orbit 객체 참조

RTC_DATA_ATTR int bootCount = 0;

// 시스템 초기화 및 부팅 원인 분석
void initSleepSystem() {
  bootCount++;
  pinMode(SLEEP_TOUCH_PIN, INPUT_PULLDOWN);

  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  
  Serial.println("\n==============================================");
  Serial.printf("  오빗(Orbit) 시스템 구동 횟수: %d회\n", bootCount);
  Serial.println("==============================================");

  if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT0) {
    Serial.println("[로그] 터치 패드 감지로 인해 시스템이 깨어났습니다");
  } else {
    Serial.println("[로그] 일반 전원 인가 또는 하드웨어 리셋");
  }
}

// 30초 후 딥슬립 진입
void checkSleepTimer(unsigned long lastActivityTime) {
  if (millis() - lastActivityTime > SLEEP_TIMEOUT_MS) {
    Serial.println("\n[시스템] 지정된 시간 동안 상호작용이 없어 딥슬립 모드로 진입합니다.");
    enterOrbitDeepSleep();
  }
}

// 터치 감지 후 깨어나기
void enterOrbitDeepSleep() {
  Serial.println("\n[설정] GPIO 14번 핀이 HIGH가 되면 깨어나도록 외부 인터럽트를 설정합니다.");
  esp_sleep_enable_ext0_wakeup(SLEEP_TOUCH_PIN, 1);

  // 1. NeoPixel LED 즉시 끄기 및 효과 중단
  stopLedEffect();
  orbit.showColor(0, 0, 0, 0);

  // 2. 진동 모터 안전 종료 (non_blocking_hw.h의 VIBE_PIN 사용)
  pinMode(VIBE_PIN, OUTPUT);
  digitalWrite(VIBE_PIN, LOW);

  Serial.flush(); // 시리얼 버퍼 비우기

  // 3. OLED 자는 눈 연출 후 절전 모드 진입
  face.playSleepAnimation();

  // 딥슬립 모드 시작
  esp_deep_sleep_start();
}