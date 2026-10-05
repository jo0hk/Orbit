#ifndef EVENT_DETECTOR_H
#define EVENT_DETECTOR_H

#include <Arduino.h>
#include "TouchHandler.h"
#include "motion.h"

// 감지된 이벤트를 상위 루프에 전달하기 위한 구조체
struct RobotEvent {
  bool isTouched;        // 일반 쓰다듬기(터치 중)
  bool isLongTouch;      // 길게 누름 (1회성 플래그)
  bool isShaken;         // 어지러움/흔들기 (1회성 플래그)
  bool stepDetected;     // 걸음 감지 (1회성 플래그)
  int currentSteps;      // 누적 걸음 수
};

void setupEventDetector(TouchHandler* touchPtr);

// loop()에서 지속 호출하며 이벤트를 감지하고 lastActivityTime을 자동으로 갱신함
RobotEvent updateEventDetector(unsigned long& lastActivityTime);

#endif