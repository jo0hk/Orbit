#ifndef TOUCH_HANDLER_H
#define TOUCH_HANDLER_H

#include <Arduino.h>

struct TouchResult {
  bool isPressed;              // 누르고 있는 상태인지 여부
  unsigned long pressDuration; // 현재까지 누르고 있던 지속 시간(ms)
};

class TouchHandler {
public:
  TouchHandler(uint8_t pin);
  void begin();
  TouchResult update();

private:
  uint8_t _pin;
  bool _isTouched;
  unsigned long _touchStartTime;
};

#endif