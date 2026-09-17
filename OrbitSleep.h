#ifndef ORBIT_SLEEP_H
#define ORBIT_SLEEP_H

#include <Arduino.h>

// 터치 센서 핀
#define SLEEP_TOUCH_PIN    GPIO_NUM_14 

// 30초 동안 아무런 조작이 없으면 딥슬립 모드 진입
#define SLEEP_TIMEOUT_MS   30000 

// RTC 메모리에 유지 (부팅 카운트)
extern RTC_DATA_ATTR int bootCount;

void initSleepSystem();
void checkSleepTimer(unsigned long lastActivityTime);
void enterOrbitDeepSleep();

#endif