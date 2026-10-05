#ifndef HARDWARE_ACTION_H
#define HARDWARE_ACTION_H

#include <Arduino.h>
#include "OrbitFace.h"

void setupHardwareAction(OrbitFace* facePtr);
void updateHardwareAction();

void applyHardwareAction(const String& led, const String& oled, const String& vibe, int stage = 0);
void setExpression(FaceExpression expr, uint32_t autoReturnMs = 0);

#endif