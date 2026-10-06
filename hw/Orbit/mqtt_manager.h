#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <Arduino.h>

// deviceId: 토픽에 그대로 사용 (orbit/{deviceId}/action, orbit/{deviceId}/status)
void setupMQTTManager(const char* deviceId);
void updateMQTTManager();           // loop()에서 지속 호출 (비차단 수신 및 재연결)

bool isMQTTConnected();
bool publishMQTT(const String& payload);  // orbit/{deviceId}/status 로 발행
void shutdownMQTT();                // 딥슬립 직전 정상 종료

#endif
