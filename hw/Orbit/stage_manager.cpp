#include "stage_manager.h"
#include "non_blocking_hw.h"

// RTC 메모리에 저장되는 현재 Stage
RTC_DATA_ATTR static int rtcCurrentStage = 0;

static StageColor currentStageColor = STAGE_COLOR_TABLE[0];

void setupStageManager() {
  // RTC 값이 범위를 벗어나면 Stage 0으로 초기화
  if (rtcCurrentStage < 0 || rtcCurrentStage > 4) {
    rtcCurrentStage = 0;
  }
  
  // ★ [수정] 딥슬립에서 깨어났을 때 현재 Stage의 테마색을 강제로 전역 변수 및 연출에 즉시 반영
  currentStageColor = STAGE_COLOR_TABLE[rtcCurrentStage];

  Serial.printf("[StageManager] 부팅/딥슬립 복귀 -> Stage %d (R:%d, G:%d, B:%d) 적용 완료\n", 
                rtcCurrentStage, currentStageColor.r, currentStageColor.g, currentStageColor.b);
}

void setStage(int newStage, bool playAnimation) {
  if (newStage < 0 || newStage > 4) {
    Serial.printf("[StageManager] 잘못된 Stage 값: %d (0~4만 가능)\n", newStage);
    return;
  }

  bool isStageChanged = (rtcCurrentStage != newStage);
  rtcCurrentStage = newStage;
  currentStageColor = STAGE_COLOR_TABLE[newStage];

  Serial.printf("[StageManager] Stage 설정 완료 -> Stage %d (R:%d, G:%d, B:%d)\n", 
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