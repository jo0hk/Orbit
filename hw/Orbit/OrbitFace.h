#ifndef ORBIT_FACE_H
#define ORBIT_FACE_H

#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

// 표정 상태 정의
enum FaceExpression {
  EXPR_NORMAL,    // 평상시 (눈 뜬 상태 + 미소)
  EXPR_BLINK,     // 눈 감은 표정
  EXPR_HAPPY,     // 기쁨
  EXPR_SAD,       // 슬픔
  EXPR_SLEEP      // 수면 모드
};

class OrbitFace {
private:
  U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2;
  FaceExpression currentExpr;
  unsigned long lastBlinkTime;
  unsigned long blinkInterval;
  bool isBlinking;

  void drawFace(bool isClosed, bool isHappy, bool isSad);

public:
  OrbitFace();
  void begin();
  void setExpression(FaceExpression expr);
  void update();             // loop()에서 주기적 깜빡임 처리
  void playWakeupAnimation(); // 기상 시 서서히 눈뜨기
  void playSleepAnimation(); // 딥슬립 직전 잠드는 표정
};

#endif