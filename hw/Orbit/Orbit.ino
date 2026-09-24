#include "OrbitLED.h"
#include "TouchHandler.h"
#include "OrbitSleep.h"
#include "OrbitFace.h"
#include "motion.h"

#define LED_PIN      18
#define TOUCH_PIN    14
#define VIB_PIN      12
#define NUMPIXELS    1
#define BRIGHT_IDLE  30

unsigned long touchResponseTime = 5000; 
unsigned long talkResponseTime  = 5000; 
unsigned long lastActivityTime  = 0;

OrbitLED orbit(NUMPIXELS, LED_PIN);
OrbitFace face;

// 딥슬립 중에도 단계 색상을 기억하도록 RTC 메모리에 저장
RTC_DATA_ATTR int curR = 135;
RTC_DATA_ATTR int curG = 206;
RTC_DATA_ATTR int curB = 250;

// 진동 패턴 제어 함수
void playVibration(int patternType) {
  if (patternType == 1) {
    // 1번: 기상 햅틱 (짧게 1회 '징-')
    digitalWrite(VIB_PIN, HIGH);
    delay(150);
    digitalWrite(VIB_PIN, LOW);
  } else if (patternType == 2) {
    // 2번: 터치/심장박동 (두근-두근 2회)
    digitalWrite(VIB_PIN, HIGH); delay(80);
    digitalWrite(VIB_PIN, LOW);  delay(100);
    digitalWrite(VIB_PIN, HIGH); delay(80);
    digitalWrite(VIB_PIN, LOW);
  }
}

void setup() {
  orbit.begin();
  face.begin();

  pinMode(TOUCH_PIN, INPUT_PULLDOWN);
  pinMode(VIB_PIN, OUTPUT);
  digitalWrite(VIB_PIN, LOW);

  Serial.begin(115200);

  setupMotion();

  // 1. 딥슬립 시스템 초기화 및 원인 진단
  initSleepSystem();

  // 2. 시스템 기상 피드백: 진동 + 눈 번쩍 뜨기 + 네오픽셀 테마색 0.5초 점등
  playVibration(1);
  face.playWakeupAnimation();
  orbit.playFadeEffect(curR, curG, curB, 500);

  lastActivityTime = millis();

  // [연동시 주석 해제] TouchHandler 내부의 와이파이 및 MQTT 초기화 호출
  // setupTouch();

  Serial.println("--- Orbit Mission Control ---");
  Serial.println("1~4: Phase Change, H: Happy, S: Sad");
}

void loop() {
  face.update();

  // 자이로 가속도 관련 코드
  static unsigned long lastMotionTick = 0;
  static unsigned long lastWalkingTime = 0;

  if (millis() - lastMotionTick >= 20) {
    lastMotionTick = millis();
    MotionResult motion = updateMotion();

    // 1) 걸음 수 체크
    if (motion.stepDetected) {
      lastActivityTime = millis();
      lastWalkingTime = millis();
      
      Serial.print("[모션] 현재 걸음: ");
      Serial.print(motion.currentSteps);
      Serial.println("보");
    }

    // 2) 흔들기 감지
    if (motion.isShaken) {
      lastActivityTime = millis();

      //  마지막으로 걸은 지 3초가 안 지났으면 어지러움 무시
      if (millis() - lastWalkingTime > 3000) {
        Serial.println("[모션] 오빗이 어지러움을 느낌");

        face.setExpression(EXPR_SAD);
        face.update();

        orbit.playFadeEffect(180, 0, 255, 1500); // 보라색 LED
        face.setExpression(EXPR_NORMAL);
      } else {
        Serial.println("[모션] 산책 중 발생한 반동이므로 어지러움 무시함");
      }
    }
  }

  // [연동시 주석 해제] 네트워크 유지 루프
  // handleTouchNetwork(); 

  // [딥슬립 상시 감시] 30초간 입력 없으면 자동 잠들기
  checkSleepTimer(lastActivityTime);

  // 1. 터치 인식 시
  if (digitalRead(TOUCH_PIN) == HIGH) {
    lastActivityTime = millis();
    
    // [연동시 주석 해제] 터치 이벤트 서버 전송
    // sendTouchMQTT(); 

    face.setExpression(EXPR_HAPPY);

    // 터치 인터랙션 시 촉각 피드백 (심장박동 패턴)
    playVibration(2);
    
    // 네오픽셀 이벤트 효과
    orbit.playFadeEffect(255, 255, 0, touchResponseTime);

    // 인터랙션 종료 후 평상시 표정으로 복귀
    face.setExpression(EXPR_NORMAL);
  }

  // 2. 시리얼 입력
  else if (Serial.available()) {
    lastActivityTime = millis();
    char input = Serial.read();

    if (input == '1') { curR = 255; curG = 60; curB = 100; orbit.playFadeEffect(curR, curG, curB, 10000); }
    else if (input == '2') { curR = 255; curG = 80; curB = 0; orbit.playFadeEffect(curR, curG, curB, 10000); }
    else if (input == '3') { curR = 127; curG = 255; curB = 0; orbit.playFadeEffect(curR, curG, curB, 10000); }
    else if (input == '4') { curR = 0; curG = 255; curB = 60; orbit.playFadeEffect(curR, curG, curB, 10000); }
    
    else if (input == 'h' || input == 'H') {
      face.setExpression(EXPR_HAPPY); // 기쁨 표정
      playVibration(2); // 기쁨 시 두근거림
      orbit.playFadeEffect(255, 255, 0, talkResponseTime);
      face.setExpression(EXPR_NORMAL); // 평상시 눈 복귀 
    }
    else if (input == 's' || input == 'S') { 
      face.setExpression(EXPR_SAD);   // 슬픔 표정
      playVibration(1); // 슬픔 시 무거운 진동
      orbit.playFadeEffect(0, 0, 255, talkResponseTime); 
      face.setExpression(EXPR_NORMAL); // 평상시 눈 복귀
    }
  }

  // 3. 평상시
  else {
    orbit.breathEffect(curR, curG, curB);
  }
}