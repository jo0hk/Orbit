#include "mqtt_manager.h"
#include "config.h"
#include "json_pipeline.h"
#include <WiFi.h>
#include <PubSubClient.h>

static WiFiClient espClient;
static PubSubClient mqttClient(espClient);

static String clientDeviceId = "Orbit_Device";
static String subTopic = "";
static String pubTopic = "";

// 비차단 지수 백오프 타이머 변수
static unsigned long lastConnectAttempt = 0;
static unsigned long retryInterval = 2000;      // 초기 재시도 간격 2초
static const unsigned long MAX_RETRY_INTERVAL = 60000; // 최대 60초까지 증가

// MQTT 토픽 수신 콜백 함수
static void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.printf("\n[MQTT RX] 토픽: %s | 메시지: %s\n", topic, message.c_str());
  
  // A-4 수신 파이프라인으로 JSON 메시지 인계
  parseAndExecuteJson(message);
}

void setupMQTTManager(const char* deviceMacId) {
  if (deviceMacId && strlen(deviceMacId) > 0) {
    clientDeviceId = "Orbit_" + String(deviceMacId);
    clientDeviceId.replace(":", ""); // MAC 주소 콜론 제거
  }

  subTopic = "orbit/" + clientDeviceId + "/command";
  pubTopic = "orbit/" + clientDeviceId + "/status";

  mqttClient.setServer(MQTT_SERVER_IP, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  Serial.printf("[MQTT] Client ID: %s 설정 완료\n", clientDeviceId.c_str());
}

static void reconnectMQTT() {
  unsigned long now = millis();

  // 지수 백오프 타임아웃을 지나지 않았으면 재연결 시도 생략 (비차단)
  if (now - lastConnectAttempt < retryInterval) return;

  lastConnectAttempt = now;

  // Wi-Fi부터 연결 확인
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[MQTT] Wi-Fi 연결 끊김 -> Wi-Fi 재연결 대기 중...");
    return;
  }

  Serial.printf("[MQTT] 서버 접속 시도 중... (%s:%d)\n", MQTT_SERVER_IP, MQTT_PORT);

  if (mqttClient.connect(clientDeviceId.c_str())) {
    Serial.println("[MQTT ⭕] 서버 연결 성공!");
    Serial.printf("[MQTT] 구독 토픽: %s\n", subTopic.c_str());
    
    mqttClient.subscribe(subTopic.c_str());
    
    // 연결 성공 시 백오프 타이머 2초로 리셋
    retryInterval = 2000; 
  } else {
    Serial.printf("[MQTT ❌] 연결 실패 (rc=%d) -> %lu초 후 재시도\n", mqttClient.state(), retryInterval / 1000);
    
    // 연결 실패 시 지수 백오프 (2초 -> 4초 -> 8초 ... 최대 60초)
    retryInterval = min(retryInterval * 2, MAX_RETRY_INTERVAL);
  }
}

void updateMQTTManager() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  } else {
    mqttClient.loop(); // 비차단 MQTT 패킷 수신 및 핑 처리
  }
}

bool isMQTTConnected() {
  return mqttClient.connected();
}

void publishMQTTStatus(const String& topic, const String& payload) {
  if (mqttClient.connected()) {
    mqttClient.publish(topic.c_str(), payload.c_str());
  }
}