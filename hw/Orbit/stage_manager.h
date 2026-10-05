#ifndef STAGE_MANAGER_H
#define STAGE_MANAGER_H

#include <Arduino.h>

struct StageColor {
  uint8_t r;
  uint8_t g;
  uint8_t b;
};

// Index 0: 디폴트 하늘색 | Index 1~4: Stage 1~4 테마색
const StageColor STAGE_COLOR_TABLE[5] = {
  {135, 206, 250}, // Stage 0: 하늘색
  {255, 60,  100}, // Stage 1: 분홍색
  {255, 80,  0  }, // Stage 2: 주황색
  {127, 255, 0  }, // Stage 3: 연두색
  {0,   255, 60 }  // Stage 4: 초록색
};

void setupStageManager();
void setStage(int newStage, bool playAnimation = true);
int getCurrentStage();
StageColor getCurrentStageColor();

#endif