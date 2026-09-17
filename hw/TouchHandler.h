#ifndef TOUCH_HANDLER_H
#define TOUCH_HANDLER_H

#include <WiFi.h>
#include <PubSubClient.h>

#define TOUCH_PIN 14

// 와이파이 및 MQTT 서버 정보
extern const char* ssid;
extern const char* password;
extern const char* mqtt_server;
extern const int mqtt_port;

extern WiFiClient espClient;
extern PubSubClient client;

// 함수 선언
void setup_wifi();
void reconnect();
void setupTouch();
void handleTouchNetwork();
void sendTouchMQTT(); // [추가] 터치 감지 시 MQTT 발행 함수

#endif