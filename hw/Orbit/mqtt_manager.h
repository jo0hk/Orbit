#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <Arduino.h>

void setupMQTTManager(const char* deviceMacId);
void updateMQTTManager(); // loop()에서 지속적으로 호출 (비차단 수신 및 재연결)

bool isMQTTConnected();
void publishMQTTStatus(const String& topic, const String& payload);

#endif