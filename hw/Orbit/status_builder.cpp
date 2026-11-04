#include "status_builder.h"
#include "config.h"
#include <ArduinoJson.h>
#include <string.h>

String buildEventJson(const char* event, int stepCount) {
  #if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
  #else
    StaticJsonDocument<128> doc;
  #endif

  doc["event"] = event;
  doc["stepCount"] = stepCount;

  String output;
  serializeJson(doc, output);
  return output;
}

String buildEventPayload(const char* event, int stepCount) {
#if STATUS_PAYLOAD_JSON
  return buildEventJson(event, stepCount);
#else
  return String(event);   // TOUCH_LONG, SHAKE, STEP_TICK 이름 그대로 발행
#endif
}

String buildStatusJson(int currentStage, int currentSteps, bool mqttConnected) {
  #if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
  #else
    StaticJsonDocument<256> doc;
  #endif

  doc["stage"] = currentStage;
  doc["steps"] = currentSteps;
  doc["mqtt"] = mqttConnected ? "connected" : "disconnected";
  doc["uptime"] = millis() / 1000;

  String output;
  serializeJson(doc, output);
  return output;
}