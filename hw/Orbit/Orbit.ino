#include <WiFi.h>
#include "config.h"
#include "TouchHandler.h"
#include "OrbitSleep.h"
#include "OrbitFace.h"
#include "OrbitLED.h"
#include "motion.h"
#include "mqtt_manager.h"
#include "event_detector.h"
#include "status_builder.h"
#include "non_blocking_hw.h"
#include "stage_manager.h"
#include "hardware_action.h"
#include "json_pipeline.h"

// 하드웨어 핀 정의
#define LED_PIN       18   
#define TOUCH_PIN     14   
#define VIB_PIN       12   
#define NUMPIXELS     1    

unsigned long lastActivityTime = 0; 
static unsigned long lastDizzyTime = 0;
String deviceId = "";               

// 하드웨어 제어 객체
OrbitLED orbit(NUMPIXELS, LED_PIN);
OrbitFace face;
TouchHandler touch(TOUCH_PIN);

void setup() {
  Serial.begin(115200);
  delay(500);

  // 1. 기본 하드웨어 초기화
  orbit.begin();
  face.begin();
  touch.begin();
  pinMode(VIB_PIN, OUTPUT);
  digitalWrite(VIB_PIN, LOW);

  setupMotion();
  initSleepSystem(); 

  // 2. 비차단 드라이버 및 파이프라인 초기화
  setupNonBlockingHW(&orbit);
  setupStageManager();
  setupHardwareAction(&face);
  setupJsonPipeline();

  // 부팅 피드백: 현재 Stage 색상으로 숨쉬기 연출
  StageColor curColor = getCurrentStageColor();
  triggerVibration(VIBE_SHORT);
  triggerBreathEffect(curColor.r, curColor.g, curColor.b, 3000);
  face.playWakeupAnimation();               
  
  lastActivityTime = millis();

  // 3. Wi-Fi 및 MQTT 설정
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - wifiStart < 3000)) { 
    delay(200);
  }
  deviceId = WiFi.macAddress();

  setupMQTTManager(deviceId.c_str());
  setupEventDetector(&touch);

  Serial.println("\n==========================================");
  Serial.println("  ORBIT FIRMWARE READY (Non-blocking)");
  Serial.println("==========================================");
}

void loop() {
  unsigned long now = millis();

  // 1. 비차단 모듈 업데이트
  updateNonBlockingHW();   
  updateHardwareAction(); 
  processJsonPipeline();  
  updateMQTTManager();    

  // 2. 센서 이벤트 감지 및 슬립 타이머 갱신
  RobotEvent event = updateEventDetector(lastActivityTime);

  static bool wasTouching = false;

  // 3. 센서 이벤트 핸들링
  // 3-1) 터치 반응
  if (event.isTouched) {
    if (!wasTouching) {
      triggerVibration(VIBE_DOUBLE);
      setExpression(EXPR_HAPPY, 0);
      triggerBreathEffect(255, 200, 0, 3000); // 손 떼기 전까지 노란빛 유지
      wasTouching = true;
    }
  } else {
    if (wasTouching) {
      setExpression(EXPR_NORMAL, 0);
      stopLedEffect(); // 평상시 Stage 색상 복귀
      wasTouching = false;
    }
  }

  // 3-2) 흔들기(어지러움) 반응
  if (event.isShaken) {
    if (now - lastDizzyTime > 3500) {
      setExpression(EXPR_DIZZY, 2000);
      triggerFadeEffect(180, 0, 255, 1200); // 보라색 연출
      lastDizzyTime = now;
    }
  }

  // 3-3) 걸음 수 디버그 로그
  if (event.stepDetected) {
    Serial.printf("[Event] STEP_TICK 감지! (현재 총 걸음 수: %d)\n", event.currentSteps);
  }

  // 4. OLED 연출 및 딥슬립 타이머 감시
  face.update(); 
  checkSleepTimer(lastActivityTime);
}