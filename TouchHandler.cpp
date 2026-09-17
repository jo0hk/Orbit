#include "TouchHandler.h"
#include "wifi_config.h"
#include <Arduino.h>

const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;
const char* mqtt_server = SECRET_MQTT_SERVER;
const int mqtt_port = SECRET_MQTT_PORT;

WiFiClient espClient;
PubSubClient client(espClient);

// 와이파이 연결 함수
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  int attempt = 0;
  while (WiFi.status() != WL_CONNECTED && attempt < 6) { // 3초 대기
    delay(500);
    Serial.print(".");
    attempt++;
  }
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected!");
}

// MQTT 재연결 함수
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("Orbit_ESP32_Yunseo")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

// 초기화 연동 함수
void setupTouch() {
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

// MQTT 연결 유지 및 루프 처리 함수
void handleTouchNetwork() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}

// [추가] 터치 인식 시 서버로 발행하는 함수
void sendTouchMQTT() {
  if (client.connected()) {
    if (client.publish("orbit/status", "TOUCHED")) {
      Serial.println("[MQTT] 서버로 TOUCHED 전송 완료");
    } else {
      Serial.println("[MQTT] 전송 실패");
    }
  }
}