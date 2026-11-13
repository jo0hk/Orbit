#ifndef EVENT_DETECTOR_H
#define EVENT_DETECTOR_H

#include <Arduino.h>
#include "TouchHandler.h"
#include "motion.h"

struct RobotEvent {
  bool isTouched;
  bool isLongTouch;
  bool isShaken;
  bool stepDetected;
  int currentSteps;
  bool isDoubleTap;   // 짧은 탭 2번 (음성 교신 시작/종료)
  unsigned long touchDuration;   // 현재 누르고 있는 시간(ms), 안 누르면 0
};

void setupEventDetector(TouchHandler* touchPtr);
RobotEvent updateEventDetector(unsigned long& lastActivityTime);

#endif