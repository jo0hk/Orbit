#include "hardware_action.h"
#include "non_blocking_hw.h"
#include "stage_manager.h"

static OrbitFace* globalFace = nullptr;
static FaceExpression currentExpr = EXPR_NORMAL;
static unsigned long exprStartTime = 0;
static uint32_t exprReturnTimeout = 0;

void setupHardwareAction(OrbitFace* facePtr) {
  globalFace = facePtr;
  setExpression(EXPR_NORMAL, 0);
}

void setExpression(FaceExpression expr, uint32_t autoReturnMs) {
  currentExpr = expr;
  exprStartTime = millis();
  exprReturnTimeout = autoReturnMs;

  if (globalFace != nullptr) {
    globalFace->setExpression(expr);
  }
  Serial.printf("[Action] OLED 표정 변경 -> %d\n", expr);
}

void updateHardwareAction() {
  if (exprReturnTimeout > 0 && currentExpr != EXPR_NORMAL) {
    if (millis() - exprStartTime >= exprReturnTimeout) {
      Serial.println("[Action] 타임아웃 -> 기본 표정 복귀");
      setExpression(EXPR_NORMAL, 0);
    }
  }
}

void applyHardwareAction(const String& led, const String& oled, const String& vibe, int stage) {
  Serial.printf("\n[Apply] Stage:%d | LED:%s | OLED:%s | VIBE:%s\n", 
                stage, led.c_str(), oled.c_str(), vibe.c_str());

  // 1. Stage 처리
  if (stage >= 1 && stage <= 4) {
    setStage(stage, true);
  }

  // 2. LED 일시 연출 처리 (Fade 후 Stage 대표색 복귀)
  if (led.length() > 0) {
    if (led.equalsIgnoreCase("rainbow") || led.equalsIgnoreCase("purple")) {
      triggerFadeEffect(255, 100, 255, 1200);
    } else if (led.equalsIgnoreCase("dim_blue") || led.equalsIgnoreCase("blue")) {
      triggerFadeEffect(0, 50, 150, 1000);
    } else if (led.equalsIgnoreCase("yellow") || led.equalsIgnoreCase("orange")) {
      triggerFadeEffect(255, 200, 0, 1500); 
    } else if (led.equalsIgnoreCase("pink")) {
      triggerFadeEffect(255, 60, 100, 1200);
    } else {
      Serial.printf("[LOG_WARN] 미지원 LED 색상: %s\n", led.c_str());
    }
  }

  // 3. 진동 처리
  if (vibe.length() > 0) {
    if (vibe.equalsIgnoreCase("short") || vibe.equalsIgnoreCase("short_pulse")) {
      triggerVibration(VIBE_SHORT);
    } else if (vibe.equalsIgnoreCase("long") || vibe.equalsIgnoreCase("soft_continuous")) {
      triggerVibration(VIBE_LONG);
    } else if (vibe.equalsIgnoreCase("double") || vibe.equalsIgnoreCase("strong_double")) {
      triggerVibration(VIBE_DOUBLE);
    }
  }

  // 4. OLED 표정 처리
  if (oled.length() > 0) {
    if (oled.equalsIgnoreCase("EXPR_HAPPY") || oled.equalsIgnoreCase("happy") || oled.equalsIgnoreCase("calm")) {
      setExpression(EXPR_HAPPY, 3000);
    } else if (oled.equalsIgnoreCase("angry") || oled.equalsIgnoreCase("dizzy") || oled.equalsIgnoreCase("EXPR_DIZZY")) {
      setExpression(EXPR_DIZZY, 3000);
    } else if (oled.equalsIgnoreCase("sad") || oled.equalsIgnoreCase("EXPR_SAD") || oled.equalsIgnoreCase("sad_eyes")) {
      setExpression(EXPR_SAD, 3000);
    } else if (oled.equalsIgnoreCase("sleep")) {
      setExpression(EXPR_SLEEP, 0);
    } else if (oled.equalsIgnoreCase("normal") || oled.equalsIgnoreCase("idle_eyes") || oled.equalsIgnoreCase("EXPR_NORMAL")) {
      setExpression(EXPR_NORMAL, 0);
    }
  }
}