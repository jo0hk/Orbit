#include "status_builder.h"
#include <ArduinoJson.h>

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