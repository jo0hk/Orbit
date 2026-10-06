#include "mqtt_manager.h"
#include "config.h"
#include "json_pipeline.h"
#include <WiFi.h>
#include <PubSubClient.h>

extern unsigned long lastActivityTime;   // Orbit.ino 전역 (서버 명령 수신도 활동으로 간주)

static WiFiClient espClient;
static PubSubClient mqttClient(espClient);

static String clientId = "";
static String subTopic = "";
static String pubTopic = "";

static unsigned long lastConnectAttempt = 0;
static unsigned long retryInterval = MQTT_RETRY_INIT_MS;

static void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message;
  message.reserve(length);
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  lastActivityTime = millis();   // 슬립 타이머 갱신

  Serial.printf("\n[MQTT RX] 토픽: %s | 메시지: %s\n", topic, message.c_str());
  parseAndExecuteJson(message);
}

void setupMQTTManager(const char* deviceId) {
  String id = (deviceId && strlen(deviceId) > 0) ? String(deviceId) : String("ORBIT-UNKNOWN");

  clientId = "orbit-" + id;
  subTopic = "orbit/" + id + "/command";
  pubTopic = "orbit/" + id + "/status";

  WiFi.setAutoReconnect(true);

  mqttClient.setServer(MQTT_SERVER_IP, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(512);     // 기본 256바이트 초과 메시지 유실 방지
  mqttClient.setSocketTimeout(2);    // 연결 시도가 loop()를 오래 막지 않도록 (초)

  Serial.printf("[MQTT] Client ID: %s\n", clientId.c_str());
  Serial.printf("[MQTT] 구독: %s | 발행: %s\n", subTopic.c_str(), pubTopic.c_str());
}

static void reconnectMQTT() {
  unsigned long now = millis();
  if (now - lastConnectAttempt < retryInterval) return;
  lastConnectAttempt = now;

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[MQTT] Wi-Fi 미연결 -> 재연결 대기 중...");
    return;
  }

  Serial.printf("[MQTT] 서버 접속 시도 (%s:%d)\n", MQTT_SERVER_IP, MQTT_PORT);

#ifdef MQTT_USER
  bool ok = mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD);
#else
  bool ok = mqttClient.connect(clientId.c_str());
#endif

  if (ok) {
    Serial.println("[MQTT] 서버 연결 성공");
    mqttClient.subscribe(subTopic.c_str());
    retryInterval = MQTT_RETRY_INIT_MS;
  } else {
    Serial.printf("[MQTT] 연결 실패 (rc=%d) -> %lu초 후 재시도\n", mqttClient.state(), retryInterval / 1000);
    retryInterval = min(retryInterval * 2, (unsigned long)MQTT_RETRY_MAX_MS);
  }
}

void updateMQTTManager() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  } else {
    mqttClient.loop();
  }
}

bool isMQTTConnected() {
  return mqttClient.connected();
}

bool publishMQTT(const String& payload) {
  if (!mqttClient.connected()) {
    Serial.println("[MQTT TX] 미연결 -> 발행 생략");
    return false;
  }
  bool ok = mqttClient.publish(pubTopic.c_str(), payload.c_str());
  Serial.printf("[MQTT TX] %s | %s (%s)\n", pubTopic.c_str(), payload.c_str(), ok ? "OK" : "FAIL");
  return ok;
}

void shutdownMQTT() {
  if (mqttClient.connected()) {
    mqttClient.disconnect();
  }
}
