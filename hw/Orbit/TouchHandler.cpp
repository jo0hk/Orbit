#include "TouchHandler.h"

TouchHandler::TouchHandler(uint8_t pin)
  : _pin(pin), _isTouched(false), _touchStartTime(0) {}

void TouchHandler::begin() {
  pinMode(_pin, INPUT); // 디지털 터치 센서(HIGH/LOW) 핀 입력 설정
}

TouchResult TouchHandler::update() {
  TouchResult result = {false, 0};
  
  // 디지털 센서: 터치 시 HIGH, 미터치 시 LOW
  bool currentlyTouched = (digitalRead(_pin) == HIGH);
  unsigned long now = millis();

  if (currentlyTouched) {
    if (!_isTouched) {
      _isTouched = true;
      _touchStartTime = now; // 터치 시작 시점 기록
    }
    result.isPressed = true;
    result.pressDuration = now - _touchStartTime;
  } else {
    _isTouched = false; // 손을 떼면 상태 초기화
  }

  return result;
}