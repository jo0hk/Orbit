#include "event_detector.h"
#include "config.h"
#include "hardware_action.h"
#include "non_blocking_hw.h"

static TouchHandler* globalTouch = nullptr;

static bool longTouchTriggered = false;
static unsigned long lastMotionTick = 0;
static unsigned long lastWalkingTime = 0;
static int lastSteps = 0;   // 모션 틱이 아닌 루프에서도 최신 걸음 수 유지

void setupEventDetector(TouchHandler* touchPtr) {
  globalTouch = touchPtr;
  setupMotion();
}

RobotEvent updateEventDetector(unsigned long& lastActivityTime) {
  RobotEvent event = { false, false, false, false, lastSteps };
  unsigned long now = millis();

  // 1. 터치 센서 이벤트 감지
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

  // 2. 가속도/자이로 센서 이벤트 감지 (10ms 틱)
  if (now - lastMotionTick >= 10) {
    lastMotionTick = now;
    MotionResult motion = updateMotion();

    lastSteps = motion.currentSteps;
    event.currentSteps = lastSteps;

    if (motion.stepDetected) {
      event.stepDetected = true;
      lastActivityTime = now;
      lastWalkingTime = now;
    }

    // 흔들기 감지 (마지막 걸음 이후 SHAKE_STILL_MS(3초) 이상 정지한 상태에서만 허용)
    if (motion.isShaken) {
      if (now - lastWalkingTime > SHAKE_STILL_MS) {
        event.isShaken = true;
        lastActivityTime = now;
        Serial.println("[Event] SHAKE 감지 (어지러움)!");
      }
    }
  }

  return event;
}
