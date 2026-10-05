#include <WiFi.h>
#include "config.h"
#include "TouchHandler.h"
#include "OrbitSleep.h"
#include "OrbitFace.h"
#include "OrbitLED.h"
#include "motion.h"
#include "mqtt_manager.h"
#include "event_detector.h"
#include "status_builder.h" // A-7 상태 빌더 추가

// 신규 비차단 모듈 포함 (A-1 ~ A-4)
#include "non_blocking_hw.h"
#include "stage_manager.h"
#include "hardware_action.h"
#include "json_pipeline.h"

// 핀 맵 정의
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

  // 1. 하드웨어 및 기본 시스템 초기화
  orbit.begin();
  face.begin();
  touch.begin();
  pinMode(VIB_PIN, OUTPUT);
  digitalWrite(VIB_PIN, LOW);

  setupMotion();
  initSleepSystem(); 

  // 2. 신규 비차단 파이프라인 모듈 초기화
  setupNonBlockingHW(&orbit);  // NeoPixel 객체(&orbit) 전달
  setupStageManager();         // RTC Stage 색상 불러오기
  setupHardwareAction(&face);  // OrbitFace 객체 연결
  setupJsonPipeline();

  // 현재 Stage 대표색 가져오기
  StageColor curColor = getCurrentStageColor();

  // 부팅 피드백 (고정 하늘색 대신 현재 Stage 대표색으로 부팅 피드백 연출)
  triggerVibration(VIBE_SHORT);
  triggerBreathEffect(curColor.r, curColor.g, curColor.b, 3000);
  face.playWakeupAnimation();
  
  lastActivityTime = millis();

  // Wi-Fi 연결 및 MAC 주소 수집
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long wifiStart = millis();
  // ★ Wi-Fi 타임아웃 구문 연산자 오타 수정 완료
  while (WiFi.status() != WL_CONNECTED && (millis() - wifiStart < 3000)) { 
    delay(200);
  }
  deviceId = WiFi.macAddress();

  setupMQTTManager(deviceId.c_str());

  Serial.println("\n==========================================");
  Serial.println("  ORBIT FIRMWARE READY (Non-blocking)");
  Serial.println("==========================================");

  setupEventDetector(&touch);
}

void loop() {
  unsigned long now = millis();

  // 1. 비차단 업데이트 파이프라인 (HW, 표정, 시리얼, MQTT)
  updateNonBlockingHW();   
  updateHardwareAction(); 
  processJsonPipeline();  
  updateMQTTManager();    

  // 2. 센서 이벤트 통합 감지 (lastActivityTime 자동 갱신)
  RobotEvent event = updateEventDetector(lastActivityTime);

  // 3. 감지된 이벤트 핸들링 (터치 & 흔들기 & 걸음)
  static bool wasTouching = false;

  // 3-1) 터치(쓰다듬기) 반응
  if (event.isTouched) {
    if (!wasTouching) {
      triggerVibration(VIBE_DOUBLE);             // 심장박동 진동 1회
      setExpression(EXPR_HAPPY, 0);               // 웃는 표정
      
      // 쓰다듬기 시작할 때 1번 호출 -> 손 뗄 때까지 노란빛 숨쉬기 유지
      triggerBreathEffect(255, 200, 0, 3000); 
      
      wasTouching = true;
    }
  } else {
    if (wasTouching) {
      setExpression(EXPR_NORMAL, 0);             // 손 떼면 평상시 표정 복귀
      stopLedEffect();                           // 노란빛 중단 후 원래 Stage 색상 복귀
      wasTouching = false;
    }
  }

  // 3-2) 흔들기(어지러움) 반응
  if (event.isShaken) {
    if (now - lastDizzyTime > 3500) {
      setExpression(EXPR_DIZZY, 2000);            // 2초 후 자동 복귀
      triggerFadeEffect(180, 0, 255, 1200);       // 보라색 연출
      lastDizzyTime = now;
    }
  }

  // 3-3) 걸음 수 디버그 로그
  if (event.stepDetected) {
    Serial.printf("[Event] STEP_TICK 감지! (현재 총 걸음 수: %d)\n", event.currentSteps);
  }

  // 4. OLED 눈 깜빡임 연출 & 딥슬립 타이머 감시
  face.update(); 
  checkSleepTimer(lastActivityTime);
}