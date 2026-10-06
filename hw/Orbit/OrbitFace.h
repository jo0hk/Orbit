#ifndef ORBIT_FACE_H
#define ORBIT_FACE_H

#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

// 표정 상태 정의
enum FaceExpression {
  EXPR_NORMAL,    // 평상시
  EXPR_BLINK,     // 눈 감음
  EXPR_HAPPY,     // 기쁨/쓰다듬기
  EXPR_SAD,       // 슬픔
  EXPR_SLEEP,     // 수면 모드
  EXPR_DIZZY,     // 어지러움
  EXPR_LISTENING, // 음성 수신 중
  EXPR_THINKING   // 생각 중
};

class OrbitFace {
private:
  U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2;
  FaceExpression currentExpr;
  unsigned long lastBlinkTime;
  unsigned long blinkInterval;
  bool isBlinking;
  unsigned long blinkStartTime;
  unsigned long blinkDuration;

  void drawFace(bool isClosed, bool isHappy, bool isSad);

public:
  OrbitFace();
  void begin();
  void setExpression(FaceExpression expr); // 표정 변경
  void update();                           // 눈 깜빡임 처리
  void playWakeupAnimation();              // 기상 시 서서히 눈뜨는 애니메이션
  void playSleepAnimation();               // 딥슬립 전 잠드는 연출 및 화면 끄기
};

#endif