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
#include "time_sync.h"
#include "voice_client.h"

// 하드웨어 핀 정의 (진동 모터 핀은 non_blocking_hw.h의 VIBE_PIN 사용)
#define LED_PIN       18
#define TOUCH_PIN     14
#define NUMPIXELS     1

unsigned long lastActivityTime = 0;   // mqtt_manager.cpp에서 extern 참조
String deviceId = "";

static unsigned long lastDizzyTime = 0;
static unsigned long bootEffectEndTime = 0;
static bool wasTouching = false;
static int pendingSteps = 0;
static bool wasMqttConnected = false;
static unsigned long lastStatusPublish = 0;

// 이벤트 발행 (payload 형식은 config.h의 STATUS_PAYLOAD_JSON에 따름, 미지원 이벤트는 생략)
static void sendEvent(const char* event, int stepCount) {
  String payload = buildEventPayload(event, stepCount);
  if (payload.length() == 0) {
    Serial.printf("[Event] %s: 현재 payload 모드에서 미지원 -> 발행 생략\n", event);
    return;
  }
  publishMQTT(payload);
}

// HW 상태 JSON 발행 (stage, steps, mqtt, uptime) - 백엔드가 steps/stage/uptime을 읽음
static void publishStatus(int steps) {
  publishMQTT(buildStatusJson(getCurrentStage(), steps, isMQTTConnected()));
}

// 하드웨어 제어 객체 (OrbitSleep.cpp에서 extern 참조)
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
  setupNonBlockingHW(&orbit);        // VIBE_PIN 초기화 포함

  // 모션 영점 보정은 진동/Wi-Fi 이전, 정지 상태에서 수행 (setupMotion은 여기서 1회만 호출)
  setupEventDetector(&touch);
  initSleepSystem();

  // 2. 상태/파이프라인 초기화
  setupStageManager();
  setupHardwareAction(&face);
  setupJsonPipeline();

  // 부팅 피드백: Stage 색상 숨쉬기(3초) + 진동 + 눈뜨기
  StageColor curColor = getCurrentStageColor();
  triggerVibration(VIBE_SHORT);
  triggerBreathEffect(curColor.r, curColor.g, curColor.b, 3000);
  bootEffectEndTime = millis() + 3000;
  face.playWakeupAnimation();

  lastActivityTime = millis();

  // 3. Wi-Fi 및 MQTT 설정 (대기 중에도 LED/진동 갱신)
  WiFi.mode(WIFI_STA);
  setupTimeSync();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - wifiStart < 3000)) {
    updateNonBlockingHW();
    delay(20);
  }

#ifdef DEVICE_ID_OVERRIDE
  deviceId = DEVICE_ID_OVERRIDE;
#else
  deviceId = WiFi.macAddress();
#endif
  Serial.printf("[Device] deviceId: %s\n", deviceId.c_str());

  setupMQTTManager(deviceId.c_str());

  // 4. 음성 교신 (마이크·스피커·광센서). 실패해도 나머지 기능은 동작
  if (!voiceBegin(deviceId.c_str())) {
    Serial.println("[Voice] 음성 교신 비활성 (마이크/스피커/파일시스템 확인)");
  }

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
  updateDailyStepReset();
  
  // 2. 센서 이벤트 감지 및 슬립 타이머 갱신
  RobotEvent event = updateEventDetector(lastActivityTime);
  
  // 상태 JSON: MQTT 접속 직후 1회 + 주기 발행
  #if STATUS_HEARTBEAT_ENABLED
    bool mqttNow = isMQTTConnected();
    if (mqttNow && (!wasMqttConnected || now - lastStatusPublish >= STATUS_HEARTBEAT_MS)) {
      publishStatus(event.currentSteps);
      lastStatusPublish = now;
    }
    wasMqttConnected = mqttNow;
  #endif

  // 부팅 숨쉬기 연출 종료 (터치 중이면 터치 연출 유지)
  if (bootEffectEndTime != 0 && now >= bootEffectEndTime) {
    if (!wasTouching) stopLedEffect();
    bootEffectEndTime = 0;
  }

  // 음성 교신 중에는 쓰다듬기·TOUCH_LONG·흔들기 반응을 끔 (녹음에 진동음 섞임·표정 덮어쓰기 방지)
  bool voiceBusy = voiceIsBusy();
  if (voiceBusy) lastActivityTime = now;   // 교신 중 딥슬립 방지

  // 3-1) 쓰다듬기 반응: PET_MIN_PRESS_MS 이상 눌러야 시작 (짧은 탭·더블탭은 표정 변화 없음)
  if (event.isTouched && !voiceBusy && event.touchDuration >= PET_MIN_PRESS_MS) {
    if (!wasTouching) {
      triggerVibration(VIBE_DOUBLE);
      setExpression(EXPR_HAPPY, 0);
      triggerBreathEffect(255, 200, 0, 3000);   // 손 떼기 전까지 노란빛 유지
      wasTouching = true;
    }
  } else {
    if (wasTouching) {
      setExpression(EXPR_NORMAL, 0);
      stopLedEffect();                          // Stage 대표색 복귀
      wasTouching = false;
    }
  }

  // 3-2) 길게 누름 -> 서버 전송
  if (event.isLongTouch && !voiceBusy) {
    sendEvent("TOUCH_LONG", event.currentSteps);
  }

  // 3-3) 흔들기(어지러움) 반응 + 서버 전송
  if (event.isShaken && !voiceBusy) {
    if (now - lastDizzyTime > 3500) {
      setExpression(EXPR_DIZZY, 2000);
      triggerFadeEffect(180, 0, 255, 1200);
      sendEvent("SHAKE", event.currentSteps);
      lastDizzyTime = now;
    }
  }

  // 3-4) 걸음 수 (묶음 전송, 기본 비활성)
  if (event.stepDetected) {
    Serial.printf("[Event] STEP 감지 (총 %d걸음)\n", event.currentSteps);
#if STEP_TICK_PUBLISH_ENABLED
    pendingSteps++;
    if (pendingSteps >= STEP_TICK_BATCH) {
      sendEvent("STEP_TICK", event.currentSteps);
      pendingSteps = 0;
    }
#endif
  }

  // 3-5) 더블탭 -> 음성 교신 시작 / 녹음 종료 / 재생 중단
  //      (터치 반응 처리 뒤에 둬야 손 뗄 때의 기본 표정 복귀가 LISTENING 표정을 덮지 않음)
  if (event.isDoubleTap) voiceOnDoubleTap();
  voiceUpdate();

  // 4. OLED 연출 및 딥슬립 타이머 감시
  face.update();
  checkSleepTimer(lastActivityTime);
}
