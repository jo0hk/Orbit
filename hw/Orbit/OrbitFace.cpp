#include "OrbitFace.h"

OrbitFace::OrbitFace() 
  : u8g2(U8G2_R0, U8X8_PIN_NONE), 
    currentExpr(EXPR_NORMAL), 
    lastBlinkTime(0), 
    blinkInterval(3000) {}

void OrbitFace::begin() {
  Wire.begin(21, 22);
  u8g2.begin();
  u8g2.setContrast(255);
  setExpression(EXPR_NORMAL);
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
    // 기쁨/쓰다듬기 (∩ ∩ 형태 곡선)
    u8g2.drawLine(x_center - eye_spacing - 8, y_center + 3, x_center - eye_spacing - 4, y_center - 2);
    u8g2.drawLine(x_center - eye_spacing - 8, y_center + 4, x_center - eye_spacing - 4, y_center - 1);
    u8g2.drawHLine(x_center - eye_spacing - 4, y_center - 3, 8);
    u8g2.drawHLine(x_center - eye_spacing - 4, y_center - 2, 8);
    u8g2.drawLine(x_center - eye_spacing + 4, y_center - 2, x_center - eye_spacing + 8, y_center + 3);
    u8g2.drawLine(x_center - eye_spacing + 4, y_center - 1, x_center - eye_spacing + 8, y_center + 4);

    u8g2.drawLine(x_center + eye_spacing - 8, y_center + 3, x_center + eye_spacing - 4, y_center - 2);
    u8g2.drawLine(x_center + eye_spacing - 8, y_center + 4, x_center + eye_spacing - 4, y_center - 1);
    u8g2.drawHLine(x_center + eye_spacing - 4, y_center - 3, 8);
    u8g2.drawHLine(x_center + eye_spacing - 4, y_center - 2, 8);
    u8g2.drawLine(x_center + eye_spacing + 4, y_center - 2, x_center + eye_spacing + 8, y_center + 3);
    u8g2.drawLine(x_center + eye_spacing + 4, y_center - 1, x_center + eye_spacing + 8, y_center + 4);
  }
  else if (currentExpr == EXPR_SAD) {
    // 슬픔 (/ \ 형태 + 오른쪽 눈물방울)
    u8g2.drawLine(x_center - eye_spacing - 6, y_center + 4, x_center - eye_spacing + 6, y_center - 2);
    u8g2.drawLine(x_center - eye_spacing - 6, y_center + 5, x_center - eye_spacing + 6, y_center - 1);
    u8g2.drawLine(x_center + eye_spacing - 6, y_center - 2, x_center + eye_spacing + 6, y_center + 4);
    u8g2.drawLine(x_center + eye_spacing - 6, y_center - 1, x_center + eye_spacing + 6, y_center + 5);

    u8g2.drawPixel(x_center + eye_spacing + 6, y_center + 8);
    u8g2.drawFilledEllipse(x_center + eye_spacing + 6, y_center + 11, 2, 3);
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
    // 어지러움 (X X 형태 교차선)
    u8g2.drawLine(x_center - eye_spacing - 8, y_center - 8, x_center - eye_spacing + 8, y_center + 8);
    u8g2.drawLine(x_center - eye_spacing - 8, y_center + 8, x_center - eye_spacing + 8, y_center - 8);
    u8g2.drawLine(x_center + eye_spacing - 8, y_center - 8, x_center + eye_spacing + 8, y_center + 8);
    u8g2.drawLine(x_center + eye_spacing - 8, y_center + 8, x_center + eye_spacing + 8, y_center - 8);
  }
  else if (currentExpr == EXPR_LISTENING) {
    // 음성 듣는 중 (가로로 긴 타원형 눈)
    u8g2.drawFilledEllipse(x_center - eye_spacing, y_center, 12, 5);
    u8g2.drawFilledEllipse(x_center + eye_spacing, y_center, 12, 5);
  }
  else if (currentExpr == EXPR_THINKING) {
    // 생각 중 (위를 쳐다보는 눈)
    u8g2.drawCircle(x_center - eye_spacing, y_center, 10);
    u8g2.drawDisc(x_center - eye_spacing, y_center - 4, 5);
    u8g2.drawCircle(x_center + eye_spacing, y_center, 10);
    u8g2.drawDisc(x_center + eye_spacing, y_center - 4, 5);
  }
  else {
    // 평상시 기본 눈 (세로 타원형)
    u8g2.drawFilledEllipse(x_center - eye_spacing, y_center, 8, 12); 
    u8g2.drawFilledEllipse(x_center + eye_spacing, y_center, 8, 12); 
  }

  // 2. 입 형태 그리기
  int mouth_y = y_center + 18;
  int mouth_width = 8;

  if (isSad || currentExpr == EXPR_DIZZY) {
    // 슬픔 또는 어지러움: 시무룩한 입 (역 V자 형태)
    u8g2.drawLine(x_center - mouth_width, mouth_y, x_center, mouth_y - 3);
    u8g2.drawLine(x_center, mouth_y - 3, x_center + mouth_width, mouth_y);
  } else {
    // 평상시 / 기쁨: 미소 짓는 입 (V자 형태)
    u8g2.drawLine(x_center - mouth_width, mouth_y - 3, x_center, mouth_y);
    u8g2.drawLine(x_center, mouth_y, x_center + mouth_width, mouth_y - 3);
  }

  u8g2.sendBuffer();
}

void OrbitFace::setExpression(FaceExpression expr) {
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

// 평상시 2.5초~5초 간격으로 눈을 깜빡이는 함수
void OrbitFace::update() {
  if (currentExpr != EXPR_NORMAL && currentExpr != EXPR_BLINK) return;

  unsigned long now = millis();
  if (now - lastBlinkTime > blinkInterval) {
    lastBlinkTime = now;
    blinkInterval = random(2500, 5000);

    setExpression(EXPR_BLINK);
    delay(random(100, 400));
    setExpression(EXPR_NORMAL);
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