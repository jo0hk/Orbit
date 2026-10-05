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
};

void setupEventDetector(TouchHandler* touchPtr);
RobotEvent updateEventDetector(unsigned long& lastActivityTime);

#endif