#include "hardware_action.h"
#include "non_blocking_hw.h"
#include "stage_manager.h"

static OrbitFace* globalFace = nullptr;
static FaceExpression currentExpr = EXPR_NORMAL;
static unsigned long exprStartTime = 0;
static uint32_t exprReturnTimeout = 0;

static const uint32_t TEMP_EXPR_MS = 3000;   // 서버 지정 표정 유지 시간

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

// 대소문자 무시 + "EXPR_" 접두어 제거
static String normalizeKey(const String& raw) {
  String key = raw;
  key.trim();
  key.toLowerCase();
  if (key.startsWith("expr_")) key.remove(0, 5);
  return key;
}

static void fadeStageColor(int stageIdx, uint16_t ms) {
  StageColor c = STAGE_COLOR_TABLE[stageIdx];
  triggerFadeEffect(c.r, c.g, c.b, ms);
}

static void applyLed(const String& key) {
  if (key == "rainbow")                       triggerFadeEffect(255, 100, 255, 1200);
  else if (key == "purple")                   triggerFadeEffect(180, 0, 255, 1200);
  else if (key == "blue" || key == "dim_blue") triggerFadeEffect(0, 50, 150, 1000);
  else if (key == "yellow")                   triggerFadeEffect(255, 200, 0, 1500);
  else if (key == "pink")                     fadeStageColor(1, 1200);
  else if (key == "orange")                   fadeStageColor(2, 1200);
  else if (key == "lime")                     fadeStageColor(3, 1200);
  else if (key == "green")                    fadeStageColor(4, 1200);
  else Serial.printf("[LOG_WARN] 미지원 LED 값: %s\n", key.c_str());
}

static void applyVibe(const String& key) {
  if (key == "short" || key == "short_pulse")            triggerVibration(VIBE_SHORT);
  else if (key == "long" || key == "soft_continuous")    triggerVibration(VIBE_LONG);
  else if (key == "double" || key == "strong_double")    triggerVibration(VIBE_DOUBLE);
  else Serial.printf("[LOG_WARN] 미지원 vibe 값: %s\n", key.c_str());
}

static void applyOled(const String& key) {
  if (key == "happy")                                         setExpression(EXPR_HAPPY, TEMP_EXPR_MS);
  else if (key == "calm" || key == "normal" || key == "idle_eyes") setExpression(EXPR_NORMAL, 0);
  else if (key == "sad" || key == "sad_eyes")                 setExpression(EXPR_SAD, TEMP_EXPR_MS);
  else if (key == "angry" || key == "dizzy")                  setExpression(EXPR_DIZZY, TEMP_EXPR_MS); // angry는 임시 매핑
  else if (key == "listening")                                setExpression(EXPR_LISTENING, 0);
  else if (key == "thinking")                                 setExpression(EXPR_THINKING, 0);
  else if (key == "sleep")                                    setExpression(EXPR_SLEEP, 0);
  else Serial.printf("[LOG_WARN] 미지원 oled 값: %s\n", key.c_str());
}

void applyHardwareAction(const String& led, const String& oled, const String& vibe, int stage) {
  Serial.printf("\n[Apply] Stage:%d | LED:%s | OLED:%s | VIBE:%s\n",
                stage, led.c_str(), oled.c_str(), vibe.c_str());

  // 1. Stage (변경될 때만 연출)
  if (stage >= 1 && stage <= 4) {
    setStage(stage, true);
  }

  // 2. LED 일시 연출 (끝나면 Stage 대표색 숨쉬기로 복귀)
  if (led.length() > 0)  applyLed(normalizeKey(led));

  // 3. 진동
  if (vibe.length() > 0) applyVibe(normalizeKey(vibe));

  // 4. OLED 표정
  if (oled.length() > 0) applyOled(normalizeKey(oled));
}
