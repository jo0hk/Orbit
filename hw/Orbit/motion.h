#ifndef MOTION_H
#define MOTION_H

#include <Arduino.h>

struct MotionResult {
  bool isShaken;
  bool stepDetected;
  int currentSteps;
};

void setupMotion();
MotionResult updateMotion();
void resetSteps();

#endif