#include <WiFi.h>
#include "wifi_config.h"
#include "TouchHandler.h"
#include "OrbitSleep.h"
#include "OrbitFace.h"
#include "OrbitLED.h"
#include "motion.h"

// 핀 맵 정의
#define LED_PIN       18   // LED 데이터 핀
#define TOUCH_PIN     14   // 터치 센서 입력 핀 (TTP223 등)
#define VIB_PIN       12   // 진동 모터 제어 핀
#define NUMPIXELS     1    // 제어할 LED 소자 개수

unsigned long lastActivityTime = 0; // 딥슬립 타이머 계산용 마지막 상호작용 시간
String deviceId = "";               // 기기 고유 식별자 (MAC 주소 기반)

// 하드웨어 제어 객체 생성
OrbitLED orbit(NUMPIXELS, LED_PIN);
OrbitFace face;
TouchHandler touch(TOUCH_PIN);

// 딥슬립 상태에서도 현재 단계별 색상을 유지하도록 RTC 메모리에 저장
RTC_DATA_ATTR int curR = 135;
RTC_DATA_ATTR int curG = 206;
RTC_DATA_ATTR int curB = 250;

// 진동 패턴 제어 (1: 기상 시 짧은 진동, 2: 심장박동 두근-두근)
void playVibration(int patternType) {
  if (patternType == 1) {
    digitalWrite(VIB_PIN, HIGH);
    delay(150);
    digitalWrite(VIB_PIN, LOW);
  } else if (patternType == 2) {
    digitalWrite(VIB_PIN, HIGH); delay(80);
    digitalWrite(VIB_PIN, LOW);  delay(100);
    digitalWrite(VIB_PIN, HIGH); delay(80);
    digitalWrite(VIB_PIN, LOW);
  }
}

// AI 응답 및 MQTT 수신용 명령 처리
void applyHardwareAction(String oledCmd, String ledCmd, String vibeCmd) {
  // 1. OLED 표정 설정
  if (oledCmd == "sad_eyes" || oledCmd == "EXPR_SAD") face.setExpression(EXPR_SAD);
  else if (oledCmd == "idle_eyes" || oledCmd == "EXPR_NORMAL") face.setExpression(EXPR_NORMAL);
  else if (oledCmd == "listening" || oledCmd == "EXPR_LISTENING") face.setExpression(EXPR_LISTENING);
  else if (oledCmd == "thinking" || oledCmd == "EXPR_THINKING") face.setExpression(EXPR_THINKING);
  else if (oledCmd == "dizzy" || oledCmd == "EXPR_DIZZY") face.setExpression(EXPR_DIZZY);
  face.update();

  // 2. LED
  if (ledCmd == "rainbow") {
    orbit.playFadeEffect(255, 100, 255, 800);
  } else if (ledCmd == "dim_blue") {
    orbit.setAllColor(0, 50, 150);
  } else if (ledCmd == "purple") {
    orbit.setAllColor(180, 0, 255);
  }

  // 3. 햅틱 진동 피드백
  if (vibeCmd == "strong_double") {
    playVibration(2);
  } else if (vibeCmd == "short" || vibeCmd == "short_pulse") {
    playVibration(1);
  } else if (vibeCmd == "soft_continuous") {
    digitalWrite(VIB_PIN, HIGH);
    delay(400);
    digitalWrite(VIB_PIN, LOW);
  }
}

void setup() {
  orbit.begin();
  face.begin();
  touch.begin();

  pinMode(VIB_PIN, OUTPUT);
  digitalWrite(VIB_PIN, LOW);

  Serial.begin(115200);
  setupMotion();
  initSleepSystem(); // 딥슬립 시스템 초기화 및 기상 원인 분석

  // 시스템 부팅/기상 피드백
  playVibration(1);
  face.playWakeupAnimation();               // 서서히 눈뜨기
  orbit.playFadeEffect(curR, curG, curB, 500); // 현재 단계 색상으로 페이드

  lastActivityTime = millis();

  // Wi-Fi 연결 및 MAC 주소 수집
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 5000) {
    delay(300);
  }

  deviceId = WiFi.macAddress();
}

void loop() {
  face.update(); // 눈 깜빡임 처리
  unsigned long now = millis();

  // 1. 가속도/자이로 감지
  static unsigned long lastMotionTick = 0;
  static unsigned long lastWalkingTime = 0;

  if (now - lastMotionTick >= 10) {
    lastMotionTick = now;
    MotionResult motion = updateMotion();

    // 1) 걸음 감지 시 활동 시간 갱신
    if (motion.stepDetected) {
      lastActivityTime = now;
      lastWalkingTime = now;
    }

    // 2) 흔들기 감지: 최근 3초간 걸음이 없던 정지 상태에서 흔들릴 때만 어지러움 반응
    if (motion.isShaken) {
      lastActivityTime = now;
      if (now - lastWalkingTime > 3000) {
        face.setExpression(EXPR_DIZZY);
        face.update();
        orbit.playFadeEffect(180, 0, 255, 1200); // 보라색
        face.setExpression(EXPR_NORMAL);
        face.update();
      }
    }
  }

  // 2. 쓰다듬기(터치)
  TouchResult touchRes = touch.update();
  static bool wasTouching = false;

  if (touchRes.isPressed) {
    lastActivityTime = now; // 터치 중 딥슬립 타이머 리셋

    // 쓰다듬기 시작하는 첫 순간에만 심장박동 진동 출력
    if (!wasTouching) {
      playVibration(2);
      wasTouching = true;
    }

    // 쓰다듬는 동안 웃는 표정 및 노란 LED 고정 
    face.setExpression(EXPR_HAPPY);
    orbit.playFadeEffect(255, 200, 0, 1000); 
  } 
  else {
    // 손을 뗐을 때 평상시 표정으로 복귀
    if (wasTouching) {
      face.setExpression(EXPR_NORMAL);
      face.update();
      wasTouching = false;
    }
    // 평상시에는 현재 단계 색상으로 숨쉬기 효과 유지
    orbit.breathEffect(curR, curG, curB);
  }

  // 3. 시리얼 테스트 명령 (단계 변경 1~4, 감정 테스트 h, s)
  if (Serial.available()) {
    lastActivityTime = now;
    char input = Serial.read();

    if (input == '1') { curR = 255; curG = 60; curB = 100; orbit.playFadeEffect(curR, curG, curB, 3000); }
    else if (input == '2') { curR = 255; curG = 80; curB = 0; orbit.playFadeEffect(curR, curG, curB, 3000); }
    else if (input == '3') { curR = 127; curG = 255; curB = 0; orbit.playFadeEffect(curR, curG, curB, 3000); }
    else if (input == '4') { curR = 0; curG = 255; curB = 60; orbit.playFadeEffect(curR, curG, curB, 3000); }
    else if (input == 'h' || input == 'H') {
      applyHardwareAction("EXPR_HAPPY", "purple", "strong_double");
      face.setExpression(EXPR_NORMAL);
      face.update();
    }
    else if (input == 's' || input == 'S') { 
      applyHardwareAction("EXPR_SAD", "dim_blue", "short");
      face.setExpression(EXPR_NORMAL);
      face.update();
    }
  }

  // 4. 딥슬립 타이머 감시 (30초간 상호작용 없으면 진입)
  checkSleepTimer(lastActivityTime);
}