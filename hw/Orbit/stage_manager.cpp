#include "stage_manager.h"
#include "non_blocking_hw.h"

RTC_DATA_ATTR static int rtcCurrentStage = 0;
static StageColor currentStageColor = STAGE_COLOR_TABLE[0];

void setupStageManager() {
  if (rtcCurrentStage < 0 || rtcCurrentStage > 4) {
    rtcCurrentStage = 0;
  }
  
  // 딥슬립 복귀 시 저장된 Stage 대표색 반영
  currentStageColor = STAGE_COLOR_TABLE[rtcCurrentStage];
  Serial.printf("[StageManager] Stage %d 복귀 (R:%d, G:%d, B:%d)\n", 
                rtcCurrentStage, currentStageColor.r, currentStageColor.g, currentStageColor.b);
}

void setStage(int newStage, bool playAnimation) {
  if (newStage < 0 || newStage > 4) {
    Serial.printf("[StageManager] 잘못된 Stage 값: %d\n", newStage);
    return;
  }

  bool isStageChanged = (rtcCurrentStage != newStage);
  rtcCurrentStage = newStage;
  currentStageColor = STAGE_COLOR_TABLE[newStage];

  Serial.printf("[StageManager] Stage 설정 -> Stage %d (R:%d, G:%d, B:%d)\n", 
                rtcCurrentStage, currentStageColor.r, currentStageColor.g, currentStageColor.b);

  if (isStageChanged && playAnimation && newStage > 0) {
    triggerVibration(VIBE_DOUBLE);
    triggerFadeEffect(currentStageColor.r, currentStageColor.g, currentStageColor.b, 1200); 
  }
}

int getCurrentStage() {
  return rtcCurrentStage;
}

StageColor getCurrentStageColor() {
  return currentStageColor;
}