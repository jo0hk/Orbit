#include "OrbitFace.h"

// 애니메이션 표정 프레임 간격 (OLED 1장 전송 동안 loop가 멈추므로 너무 짧게 잡지 않음)
static const uint16_t DIZZY_FRAME_MS    = 120;
static const uint16_t THINKING_FRAME_MS = 400;

OrbitFace::OrbitFace()
  : u8g2(U8G2_R0, U8X8_PIN_NONE),
    currentExpr(EXPR_NORMAL),
    lastBlinkTime(0),
    blinkInterval(3000),
    isBlinking(false),
    blinkStartTime(0),
    blinkDuration(0),
    animFrame(0),
    lastAnimTime(0) {}

void OrbitFace::begin() {
  Wire.begin(21, 22);
  u8g2.begin();
  u8g2.setContrast(255);

  // OLED 1프레임 그리는 시간 측정 (애니메이션 간격 조정용)
  unsigned long t0 = micros();
  setExpression(EXPR_NORMAL);
  Serial.printf("[Face] 1프레임 그리기 %lu ms\n", (micros() - t0) / 1000);
}

void OrbitFace::drawFace(bool isClosed, bool isHappy, bool isSad) {
  u8g2.clearBuffer();

  int x_center = 64;
  int y_center = 28;
  int eye_spacing = 24;

  // 1. 눈 그리기
  if (isClosed) {
    // 눈 감음 (단순 수평선)
    u8g2.drawHLine(x_center - eye_spacing - 8, y_center + 2, 16); 
    u8g2.drawHLine(x_center + eye_spacing - 8, y_center + 2, 16); 
  } 
  else if (isHappy) {
    // 기쁨/쓰다듬기 (두꺼운 반달 눈 ∩ + 볼터치 ///)
    for (int side = 0; side < 2; side++) {
      int cx = (side == 0) ? x_center - eye_spacing : x_center + eye_spacing;
      u8g2.drawFilledEllipse(cx, y_center + 2, 9, 8);
      u8g2.setDrawColor(0);
      u8g2.drawFilledEllipse(cx, y_center + 5, 6, 7);   // 안쪽 파내기
      u8g2.drawBox(cx - 10, y_center + 3, 21, 10);      // 아래쪽 잘라 반달 모양
      u8g2.setDrawColor(1);
      for (int k = 0; k < 3; k++) {
        u8g2.drawLine(cx - 6 + k * 4, y_center + 14, cx - 4 + k * 4, y_center + 11);
      }
    }
  }
  else if (currentExpr == EXPR_SAD) {
    // 슬픔 (꽉 찬 눈의 바깥쪽 위를 비스듬히 잘라 처진 눈 + 오른쪽 눈물방울)
    int lx = x_center - eye_spacing, rx = x_center + eye_spacing;
    u8g2.drawFilledEllipse(lx, y_center + 2, 9, 9);
    u8g2.drawFilledEllipse(rx, y_center + 2, 9, 9);
    u8g2.setDrawColor(0);
    u8g2.drawTriangle(lx - 11, y_center - 9, lx + 11, y_center - 9, lx - 11, y_center + 1);
    u8g2.drawTriangle(rx - 11, y_center - 9, rx + 11, y_center - 9, rx + 11, y_center + 1);
    u8g2.setDrawColor(1);
    u8g2.drawFilledEllipse(rx + 10, y_center + 12, 2, 3);   // 눈물
  }
  else if (currentExpr == EXPR_SLEEP) {
    // 자는 눈 (u u 형태 + 우측 zZ 문자열)
    u8g2.drawLine(x_center - eye_spacing - 7, y_center, x_center - eye_spacing - 3, y_center + 4);
    u8g2.drawLine(x_center - eye_spacing - 7, y_center + 1, x_center - eye_spacing - 3, y_center + 5);
    u8g2.drawHLine(x_center - eye_spacing - 3, y_center + 4, 6);
    u8g2.drawHLine(x_center - eye_spacing - 3, y_center + 5, 6);
    u8g2.drawLine(x_center - eye_spacing + 3, y_center + 4, x_center - eye_spacing + 7, y_center);
    u8g2.drawLine(x_center - eye_spacing + 3, y_center + 5, x_center - eye_spacing + 7, y_center + 1);

    u8g2.drawLine(x_center + eye_spacing - 7, y_center, x_center + eye_spacing - 3, y_center + 4);
    u8g2.drawLine(x_center + eye_spacing - 7, y_center + 1, x_center + eye_spacing - 3, y_center + 5);
    u8g2.drawHLine(x_center + eye_spacing - 3, y_center + 4, 6);
    u8g2.drawHLine(x_center + eye_spacing - 3, y_center + 5, 6);
    u8g2.drawLine(x_center + eye_spacing + 3, y_center + 4, x_center + eye_spacing + 7, y_center);
    u8g2.drawLine(x_center + eye_spacing + 3, y_center + 5, x_center + eye_spacing + 7, y_center + 1);

    u8g2.setFont(u8g2_font_5x7_tf);
    u8g2.drawStr(x_center + 26, y_center - 10, "z");
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(x_center + 34, y_center - 16, "Z");
  }
  else if (currentExpr == EXPR_DIZZY) {
    // 어지러움 (소용돌이 눈, 프레임마다 회전. 양쪽 눈은 반대 방향)
    for (int side = 0; side < 2; side++) {
      int cx = (side == 0) ? x_center - eye_spacing : x_center + eye_spacing;
      float dir = (side == 0) ? 1.0f : -1.0f;
      int px = 0, py = 0;
      for (int i = 0; i < 64; i++) {
        float t = i * 0.2f;
        float r = 0.75f * t + 0.5f;                 // 바깥으로 갈수록 반지름 증가
        float a = dir * (t + animFrame * 0.9f);     // 회전
        int x = (int)lroundf(cx + r * cosf(a));
        int y = (int)lroundf(y_center + r * sinf(a));
        if (i > 0) u8g2.drawLine(px, py, x, y);
        px = x; py = y;
      }
    }
  }
  else if (currentExpr == EXPR_LISTENING) {
    // 음성 듣는 중 (가로로 긴 타원형 눈)
    u8g2.drawFilledEllipse(x_center - eye_spacing, y_center, 12, 5);
    u8g2.drawFilledEllipse(x_center + eye_spacing, y_center, 12, 5);
  }
  else if (currentExpr == EXPR_THINKING) {
    // 생각 중 (오른쪽 위를 보는 눈 + 한쪽 눈썹 올림 + 말줄임표 점이 하나씩 생김 0~3개 반복)
    int lx = x_center - eye_spacing, rx = x_center + eye_spacing;
    u8g2.drawFilledEllipse(lx + 3, y_center - 3, 7, 10);
    u8g2.drawFilledEllipse(rx + 3, y_center - 3, 7, 10);
    u8g2.drawHLine(lx - 7, y_center - 15, 15);                           // 왼쪽 눈썹: 평평
    u8g2.drawLine(rx - 6, y_center - 17, rx + 8, y_center - 19);         // 오른쪽 눈썹: 올라감 (2px)
    u8g2.drawLine(rx - 6, y_center - 16, rx + 8, y_center - 18);
    for (int k = 0; k < animFrame % 4; k++) {
      u8g2.drawDisc(x_center + 44 + k * 6, y_center - 22, 1);            // 말줄임표 점
    }
  }
  else if (currentExpr == EXPR_ANGRY) {
    // 화남 (노려보는 눈: 꽉 찬 원의 안쪽 위를 비스듬히 잘라냄 + 안쪽으로 내려간 눈썹)
    int lx = x_center - eye_spacing, rx = x_center + eye_spacing;
    u8g2.drawFilledEllipse(lx, y_center + 2, 9, 9);
    u8g2.drawFilledEllipse(rx, y_center + 2, 9, 9);
    u8g2.setDrawColor(0);
    u8g2.drawTriangle(lx - 11, y_center - 8, lx + 11, y_center - 8, lx + 11, y_center + 1);
    u8g2.drawTriangle(rx - 11, y_center - 8, rx + 11, y_center - 8, rx - 11, y_center + 1);
    u8g2.setDrawColor(1);
    for (int o = 0; o < 3; o++) {   // 눈썹 3px 두께
      u8g2.drawLine(lx - 10, y_center - 14 + o, lx + 9, y_center - 7 + o);
      u8g2.drawLine(rx + 10, y_center - 14 + o, rx - 9, y_center - 7 + o);
    }
  }
  else if (currentExpr == EXPR_CALM) {
    // 차분함 (편안하게 반쯤 감은 눈 + 볼터치 ///)
    for (int side = 0; side < 2; side++) {
      int cx = (side == 0) ? x_center - eye_spacing : x_center + eye_spacing;
      u8g2.drawFilledEllipse(cx, y_center + 1, 9, 7);
      u8g2.setDrawColor(0);
      u8g2.drawBox(cx - 10, y_center - 7, 21, 7);   // 위쪽 절반 지우기
      u8g2.setDrawColor(1);
      u8g2.drawHLine(cx - 10, y_center, 21);         // 눈꺼풀 선
      for (int k = 0; k < 3; k++) {
        u8g2.drawLine(cx - 6 + k * 4, y_center + 14, cx - 4 + k * 4, y_center + 11);
      }
    }
  }
  else {
    // 평상시 기본 눈 (세로 타원형)
    u8g2.drawFilledEllipse(x_center - eye_spacing, y_center, 8, 12); 
    u8g2.drawFilledEllipse(x_center + eye_spacing, y_center, 8, 12); 
  }

  // 2. 입 형태 그리기
  int mouth_y = y_center + 18;
  int mouth_width = 8;

  if (currentExpr == EXPR_ANGRY) {
    // 화남: 꾹 다문 일자 입
    u8g2.drawHLine(x_center - 7, mouth_y - 1, 15);
    u8g2.drawHLine(x_center - 7, mouth_y, 15);
  } else if (currentExpr == EXPR_DIZZY) {
    // 어지러움: 꿈틀거리는 물결 입 (프레임마다 움직임)
    int px = 0, py = 0;
    for (int i = 0; i <= 20; i++) {
      int x = x_center - 10 + i;
      int y = mouth_y - 1 + (int)lroundf(1.5f * sinf(i * 0.9f + animFrame));
      if (i > 0) u8g2.drawLine(px, py, x, y);
      px = x; py = y;
    }
  } else if (currentExpr == EXPR_THINKING) {
    // 생각 중: 한쪽으로 삐죽 올라간 입 (2px)
    u8g2.drawLine(x_center - 2, mouth_y + 1, x_center + 6, mouth_y - 1);
    u8g2.drawLine(x_center - 2, mouth_y + 2, x_center + 6, mouth_y);
  } else if (currentExpr == EXPR_CALM) {
    // 차분함: 작은 미소
    u8g2.drawLine(x_center - 6, mouth_y - 2, x_center, mouth_y + 1);
    u8g2.drawLine(x_center, mouth_y + 1, x_center + 6, mouth_y - 2);
  } else if (isSad) {
    // 슬픔: 굵은 시무룩한 입 (역 V자, 2px)
    for (int o = 0; o < 2; o++) {
      u8g2.drawLine(x_center - 7, mouth_y + 1 + o, x_center, mouth_y - 2 + o);
      u8g2.drawLine(x_center, mouth_y - 2 + o, x_center + 7, mouth_y + 1 + o);
    }
  } else if (isHappy) {
    // 기쁨: 활짝 벌린 웃는 입 (아래쪽 반원)
    u8g2.drawFilledEllipse(x_center, mouth_y - 1, 7, 5, U8G2_DRAW_LOWER_LEFT | U8G2_DRAW_LOWER_RIGHT);
  } else {
    // 평상시: 미소 짓는 입 (V자 형태)
    u8g2.drawLine(x_center - mouth_width, mouth_y - 3, x_center, mouth_y);
    u8g2.drawLine(x_center, mouth_y, x_center + mouth_width, mouth_y - 3);
  }

  u8g2.sendBuffer();
}

void OrbitFace::setExpression(FaceExpression expr) {
  if (expr != currentExpr) {   // 새 표정이면 애니메이션 처음부터
    animFrame = 0;
    lastAnimTime = millis();
  }
  currentExpr = expr;
  switch (currentExpr) {
    case EXPR_NORMAL:    drawFace(false, false, false); break;
    case EXPR_BLINK:     drawFace(true, false, false);  break;
    case EXPR_HAPPY:     drawFace(false, true, false);  break;
    case EXPR_SAD:       drawFace(false, false, true);  break;
    case EXPR_SLEEP:
    case EXPR_DIZZY:
    case EXPR_LISTENING:
    case EXPR_THINKING:
    case EXPR_ANGRY:
    case EXPR_CALM:
      drawFace(false, false, false);
      break;
  }
}

// 부팅/기상 시 세로 폭을 넓히며 서서히 눈뜨는 연출
void OrbitFace::playWakeupAnimation() {
  int x_center = 64;
  int y_center = 28;
  int eye_spacing = 24;

  for (int h = 1; h <= 12; h += 3) {
    u8g2.clearBuffer();
    u8g2.drawFilledEllipse(x_center - eye_spacing, y_center, 8, h);
    u8g2.drawFilledEllipse(x_center + eye_spacing, y_center, 8, h);
    u8g2.sendBuffer();
    delay(40);
  }
  setExpression(EXPR_NORMAL);
}

// 평상시 2.5초~5초 간격으로 눈을 깜빡이는 함수 (비차단)
void OrbitFace::update() {
  unsigned long now = millis();

  if (isBlinking) {
    if (currentExpr != EXPR_BLINK) {   // 깜빡임 중 다른 표정으로 바뀐 경우
      isBlinking = false;
      return;
    }
    if (now - blinkStartTime >= blinkDuration) {
      isBlinking = false;
      setExpression(EXPR_NORMAL);
    }
    return;
  }

  // 애니메이션 표정: 정해진 간격마다 다음 프레임 그리기
  if (currentExpr == EXPR_DIZZY || currentExpr == EXPR_THINKING) {
    uint16_t interval = (currentExpr == EXPR_DIZZY) ? DIZZY_FRAME_MS : THINKING_FRAME_MS;
    if (now - lastAnimTime >= interval) {
      lastAnimTime = now;
      animFrame++;
      drawFace(false, false, false);
    }
    return;
  }

  if (currentExpr != EXPR_NORMAL) return;

  if (now - lastBlinkTime > blinkInterval) {
    lastBlinkTime = now;
    blinkInterval = random(2500, 5000);
    blinkDuration = random(100, 400);
    blinkStartTime = now;
    isBlinking = true;
    setExpression(EXPR_BLINK);
  }
}

// 딥슬립 진입 전 잠드는 연출 (자는 눈 4초 유지 후 OLED 절전)
void OrbitFace::playSleepAnimation() {
  setExpression(EXPR_SLEEP);
  delay(4000);
  u8g2.clearBuffer();
  u8g2.sendBuffer();
  u8g2.setPowerSave(1); // OLED 패널 전원 절전 모드
}