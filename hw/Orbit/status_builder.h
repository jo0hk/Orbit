#ifndef STATUS_BUILDER_H
#define STATUS_BUILDER_H

#include <Arduino.h>

// 현재 오빗의 상태(Stage, 걸음 수, MQTT 연결 여부 등)를 JSON 문자열로 생성
String buildStatusJson(int currentStage, int currentSteps, bool mqttConnected);

#endif