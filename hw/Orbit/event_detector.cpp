#include "event_detector.h"
#include "hardware_action.h"
#include "non_blocking_hw.h"

static TouchHandler* globalTouch = nullptr;

static bool longTouchTriggered = false;
static unsigned long lastMotionTick = 0;
static unsigned long lastWalkingTime = 0;

void setupEventDetector(TouchHandler* touchPtr) {
  globalTouch = touchPtr;
  setupMotion();
}

RobotEvent updateEventDetector(unsigned long& lastActivityTime) {
  RobotEvent event = { false, false, false, false, 0 };
  unsigned long now = millis();

  // 1. 터치 센서 감지
  if (globalTouch != nullptr) {
    TouchResult touchRes = globalTouch->update();

    if (touchRes.isPressed) {
      event.isTouched = true;
      lastActivityTime = now;

      if (touchRes.pressDuration >= 1500 && !longTouchTriggered) {
        event.isLongTouch = true;
        longTouchTriggered = true;
        Serial.println("[Event] TOUCH_LONG 감지!");
      }
    } else {
      longTouchTriggered = false;
    }
  }

  // 2. Motion 감지 (10ms 틱)
  if (now - lastMotionTick >= 10) {
    lastMotionTick = now;
    MotionResult motion = updateMotion();

    event.currentSteps = motion.currentSteps;

    // ★ 걸음 수가 감지되었거나, 혹은 걸음 수가 안 찍혀도 가속도가 1.2g 이상으로 계속 움직이는 중이면 활동 중으로 간주하여 어지러움 차단 타이머 연장
    if (motion.stepDetected) {
      event.stepDetected = true;
      lastActivityTime = now;
      lastWalkingTime = now;
    }

    // 2) 흔들기 감지: 차단 기준 시간을 3초(3000ms) -> 0.8초(800ms)로 대폭 단축
    // (또는 자이로 회전이 일정 이상 강할 때는 걷기 쿨다운 무시)
    if (motion.isShaken) {
      if (now - lastWalkingTime > 800) {  // 3000 -> 800으로 완화
        event.isShaken = true;
        lastActivityTime = now;
        Serial.println("[Event] SHAKE 감지 (어지러움)!");
      }
    }
  }

  return event;
}