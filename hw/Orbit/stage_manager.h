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
  {0,   200, 180}, // Stage 1: 청록
  {0,   255, 60 }, // Stage 2: 민트
  {255, 150, 0  }, // Stage 3: 주황
  {255, 90,  70 }  // Stage 4: 핑크
};

void setupStageManager();
void setStage(int newStage, bool playAnimation = true);
int getCurrentStage();
StageColor getCurrentStageColor();

#endif