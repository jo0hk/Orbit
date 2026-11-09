#include "time_sync.h"
#include "motion.h"
#include <Arduino.h>
#include <WiFi.h>
#include <time.h>

#define TZ_KST "KST-9"
static const time_t VALID_EPOCH = 1700000000;   // 이보다 작으면 시각 미동기화로 간주

RTC_DATA_ATTR static int rtcStepDay = 0;        // yyyymmdd, 딥슬립 간 유지 (전원 차단 시 0)
static bool ntpStarted = false;
static unsigned long lastCheck = 0;

void setupTimeSync() {
  // 딥슬립 기상 후 Wi-Fi 없이도 날짜를 KST로 계산하도록 TZ를 먼저 지정
  setenv("TZ", TZ_KST, 1);
  tzset();
}

static int todayKey() {
  time_t now = time(nullptr);
  if (now < VALID_EPOCH) return 0;
  struct tm t;
  localtime_r(&now, &t);
  return (t.tm_year + 1900) * 10000 + (t.tm_mon + 1) * 100 + t.tm_mday;
}

void updateDailyStepReset() {
  unsigned long ms = millis();
  if (ms - lastCheck < 1000) return;
  lastCheck = ms;

  // Wi-Fi 연결 후 1회 시작 (이후 SNTP가 백그라운드에서 주기적으로 재동기화)
  if (!ntpStarted && WiFi.status() == WL_CONNECTED) {
    configTzTime(TZ_KST, "pool.ntp.org", "time.google.com");
    ntpStarted = true;
    Serial.println("[Time] NTP 동기화 시작");
  }

  int today = todayKey();
  if (today == 0) return;                                // 시각 미확정 -> 리셋 안 함
  if (rtcStepDay == 0) { rtcStepDay = today; return; }   // 첫 기록
  if (today != rtcStepDay) {
    Serial.printf("[Time] 날짜 변경 %d -> %d : 걸음 수 초기화\n", rtcStepDay, today);
    resetSteps();
    rtcStepDay = today;
  }
}