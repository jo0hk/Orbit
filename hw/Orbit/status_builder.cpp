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
  // 백엔드 현재 처리 문자열: TOUCHED, FUEL_UP, LOVE_UP, happy, sad, angry, calm
  if (strcmp(event, "TOUCH_LONG") == 0) return String("TOUCHED");
  return String("");   // SHAKE, STEP_TICK은 미지원 -> 발행 생략
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