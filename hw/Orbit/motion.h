#ifndef MOTION_H
#define MOTION_H

#include <Arduino.h>

// 가속도/자이로 분석 결과 구조체
struct MotionResult {
  bool isShaken;
  bool stepDetected;
  int currentSteps;
};

void setupMotion();
MotionResult updateMotion();
void resetSteps();

#endif