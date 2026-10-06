#include "stage_manager.h"
#include "non_blocking_hw.h"
#include <Preferences.h>

// NVS(플래시)에 저장하므로 딥슬립은 물론 전원이 꺼져도 Stage가 유지됨
static Preferences prefs;
static const char* NVS_NAMESPACE = "orbit";
static const char* NVS_KEY_STAGE = "stage";

static int currentStage = 0;
static StageColor currentStageColor = STAGE_COLOR_TABLE[0];

void setupStageManager() {
  if (prefs.begin(NVS_NAMESPACE, false)) {
    currentStage = prefs.getUChar(NVS_KEY_STAGE, 0);
    prefs.end();
  } else {
    Serial.println("[StageManager] NVS 열기 실패 -> Stage 0으로 시작");
    currentStage = 0;
  }

  if (currentStage < 0 || currentStage > 4) {
    currentStage = 0;
  }

  currentStageColor = STAGE_COLOR_TABLE[currentStage];
  Serial.printf("[StageManager] 저장된 Stage %d 복원 (R:%d, G:%d, B:%d)\n",
                currentStage, currentStageColor.r, currentStageColor.g, currentStageColor.b);
}

void setStage(int newStage, bool playAnimation) {
  if (newStage < 0 || newStage > 4) {
    Serial.printf("[StageManager] 잘못된 Stage 값: %d\n", newStage);
    return;
  }

  bool isStageChanged = (currentStage != newStage);
  currentStage = newStage;
  currentStageColor = STAGE_COLOR_TABLE[newStage];

  Serial.printf("[StageManager] Stage 설정 -> Stage %d (R:%d, G:%d, B:%d)\n",
                currentStage, currentStageColor.r, currentStageColor.g, currentStageColor.b);

  // 값이 바뀔 때만 저장 (플래시 쓰기 횟수 최소화)
  if (isStageChanged) {
    if (prefs.begin(NVS_NAMESPACE, false)) {
      prefs.putUChar(NVS_KEY_STAGE, (uint8_t)currentStage);
      prefs.end();
    } else {
      Serial.println("[StageManager] NVS 저장 실패");
    }
  }

  if (isStageChanged && playAnimation && newStage > 0) {
    triggerVibration(VIBE_DOUBLE);
    triggerFadeEffect(currentStageColor.r, currentStageColor.g, currentStageColor.b, 1200);
  }
}

int getCurrentStage() {
  return currentStage;
}

StageColor getCurrentStageColor() {
  return currentStageColor;
}
