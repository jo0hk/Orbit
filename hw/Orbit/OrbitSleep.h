#ifndef ORBIT_SLEEP_H
#define ORBIT_SLEEP_H

#include <Arduino.h>

#define SLEEP_TOUCH_PIN    GPIO_NUM_14 
#define SLEEP_TIMEOUT_MS   30000 

extern RTC_DATA_ATTR int bootCount;

void initSleepSystem();
void checkSleepTimer(unsigned long lastActivityTime);
void enterOrbitDeepSleep();

#endif