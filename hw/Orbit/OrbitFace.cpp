#include "OrbitFace.h"

OrbitFace::OrbitFace() 
  : u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE), 
    currentExpr(EXPR_NORMAL), 
    lastBlinkTime(0), 
    blinkInterval(3000), 
    isBlinking(false) {}

void OrbitFace::begin() {
  Wire.begin(21, 22);
  u8g2.begin();
  u8g2.setContrast(255);
  setExpression(EXPR_NORMAL);
}

// 검증된 드로잉 함수 기반 렌더링
void OrbitFace::drawFace(bool isClosed, bool isHappy, bool isSad) {
  u8g2.clearBuffer();

  int x_center = 64;
  int y_center = 28;
  int eye_spacing = 24;

  // 1. 눈 그리기
  if (isClosed) {
    // 눈 감음 (수평선)
    u8g2.drawHLine(x_center - eye_spacing - 8, y_center + 2, 16); 
    u8g2.drawHLine(x_center + eye_spacing - 8, y_center + 2, 16); 
  } 
  else if (isHappy) {
    // [기쁨 눈: (∩ ∩ 형태)]
    // 왼쪽 눈
    u8g2.drawLine(x_center - eye_spacing - 8, y_center + 3, x_center - eye_spacing - 4, y_center - 2);
    u8g2.drawLine(x_center - eye_spacing - 8, y_center + 4, x_center - eye_spacing - 4, y_center - 1);

    u8g2.drawHLine(x_center - eye_spacing - 4, y_center - 3, 8); // 상단 평평한 둥근 구간
    u8g2.drawHLine(x_center - eye_spacing - 4, y_center - 2, 8);

    u8g2.drawLine(x_center - eye_spacing + 4, y_center - 2, x_center - eye_spacing + 8, y_center + 3);
    u8g2.drawLine(x_center - eye_spacing + 4, y_center - 1, x_center - eye_spacing + 8, y_center + 4);

    // 오른쪽 눈
    u8g2.drawLine(x_center + eye_spacing - 8, y_center + 3, x_center + eye_spacing - 4, y_center - 2);
    u8g2.drawLine(x_center + eye_spacing - 8, y_center + 4, x_center + eye_spacing - 4, y_center - 1);

    u8g2.drawHLine(x_center + eye_spacing - 4, y_center - 3, 8); // 상단 평평한 둥근 구간
    u8g2.drawHLine(x_center + eye_spacing - 4, y_center - 2, 8);

    u8g2.drawLine(x_center + eye_spacing + 4, y_center - 2, x_center + eye_spacing + 8, y_center + 3);
    u8g2.drawLine(x_center + eye_spacing + 4, y_center - 1, x_center + eye_spacing + 8, y_center + 4);
  }
  else if (currentExpr == EXPR_SAD) {
    // [슬픔 눈: / \ 형태]
    // 왼쪽
    u8g2.drawLine(x_center - eye_spacing - 6, y_center + 4, x_center - eye_spacing + 6, y_center - 2);
    u8g2.drawLine(x_center - eye_spacing - 6, y_center + 5, x_center - eye_spacing + 6, y_center - 1);

    // 오른쪽
    u8g2.drawLine(x_center + eye_spacing - 6, y_center - 2, x_center + eye_spacing + 6, y_center + 4);
    u8g2.drawLine(x_center + eye_spacing - 6, y_center - 1, x_center + eye_spacing + 6, y_center + 5);

    // [눈물방울: 물방울 형태 (위쪽 점 + 아래 타원)]
    // 오른쪽 눈물
    u8g2.drawPixel(x_center + eye_spacing + 6, y_center + 8);
    u8g2.drawFilledEllipse(x_center + eye_spacing + 6, y_center + 11, 2, 3);
  }
  else if (currentExpr == EXPR_SLEEP) {
    // [자는 눈: u u 형태]
    // 왼쪽 눈 (2픽셀 두께 아치형)
    u8g2.drawLine(x_center - eye_spacing - 7, y_center, x_center - eye_spacing - 3, y_center + 4);
    u8g2.drawLine(x_center - eye_spacing - 7, y_center + 1, x_center - eye_spacing - 3, y_center + 5);

    u8g2.drawHLine(x_center - eye_spacing - 3, y_center + 4, 6);
    u8g2.drawHLine(x_center - eye_spacing - 3, y_center + 5, 6);

    u8g2.drawLine(x_center - eye_spacing + 3, y_center + 4, x_center - eye_spacing + 7, y_center);
    u8g2.drawLine(x_center - eye_spacing + 3, y_center + 5, x_center - eye_spacing + 7, y_center + 1);

    // 오른쪽 눈 (2픽셀 두께 아치형)
    u8g2.drawLine(x_center + eye_spacing - 7, y_center, x_center + eye_spacing - 3, y_center + 4);
    u8g2.drawLine(x_center + eye_spacing - 7, y_center + 1, x_center + eye_spacing - 3, y_center + 5);

    u8g2.drawHLine(x_center + eye_spacing - 3, y_center + 4, 6);
    u8g2.drawHLine(x_center + eye_spacing - 3, y_center + 5, 6);

    u8g2.drawLine(x_center + eye_spacing + 3, y_center + 4, x_center + eye_spacing + 7, y_center);
    u8g2.drawLine(x_center + eye_spacing + 3, y_center + 5, x_center + eye_spacing + 7, y_center + 1);

    // 머리 위 떠오르는 z Z 텍스트
    u8g2.setFont(u8g2_font_5x7_tf);
    u8g2.drawStr(x_center + 26, y_center - 10, "z");
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(x_center + 34, y_center - 16, "Z");
  }
  else {
    // 기본 눈 (타원형)
    u8g2.drawFilledEllipse(x_center - eye_spacing, y_center, 8, 12); 
    u8g2.drawFilledEllipse(x_center + eye_spacing, y_center, 8, 12); 
  }

  // 2. 입 그리기
  int mouth_y = y_center + 18;
  int mouth_width = 8;

  if (isSad) {
    // 시무룩한 입 (역 V자 형태)
    u8g2.drawLine(x_center - mouth_width, mouth_y, x_center, mouth_y - 3);
    u8g2.drawLine(x_center, mouth_y - 3, x_center + mouth_width, mouth_y);
  } else {
    // 입꼬리 올라간 미소 (V자 형태)
    u8g2.drawLine(x_center - mouth_width, mouth_y - 3, x_center, mouth_y);
    u8g2.drawLine(x_center, mouth_y, x_center + mouth_width, mouth_y - 3);
  }

  u8g2.sendBuffer();
}

void OrbitFace::setExpression(FaceExpression expr) {
  currentExpr = expr;
  switch (currentExpr) {
    case EXPR_NORMAL:
      drawFace(false, false, false);
      break;
    case EXPR_BLINK:
      drawFace(true, false, false);
      break;
    case EXPR_HAPPY:
      drawFace(false, true, false);
      break;
    case EXPR_SAD:
      drawFace(false, false, true);
      break;
    case EXPR_SLEEP:
      drawFace(false, false, false);
      break;
  }
}

// 기상 시 서서히 눈뜨는 애니메이션
void OrbitFace::playWakeupAnimation() {
  int x_center = 64;
  int y_center = 28;
  int eye_spacing = 24;

  // 감은 눈에서 타원으로 점점 커짐
  for (int h = 1; h <= 12; h += 3) {
    u8g2.clearBuffer();
    u8g2.drawFilledEllipse(x_center - eye_spacing, y_center, 8, h);
    u8g2.drawFilledEllipse(x_center + eye_spacing, y_center, 8, h);
    u8g2.sendBuffer();
    delay(40);
  }
  setExpression(EXPR_NORMAL);
}

// 눈 깜빡임 제어
void OrbitFace::update() {
  if (currentExpr != EXPR_NORMAL && currentExpr != EXPR_BLINK) return;

  unsigned long now = millis();
  if (now - lastBlinkTime > blinkInterval) {
    lastBlinkTime = now;
    blinkInterval = random(2500, 5000); // 깜빡임 간격

    // 눈 깜빡임
    setExpression(EXPR_BLINK);
    delay(random(100, 400));
    setExpression(EXPR_NORMAL);
  }
}

// 딥슬립 진입 전 잠드는 연출
void OrbitFace::playSleepAnimation() {
  setExpression(EXPR_SLEEP);
  delay(4000);
  
  // 절전을 위해 화면 끄기
  u8g2.clearBuffer();
  u8g2.sendBuffer();
  u8g2.setPowerSave(1);
}