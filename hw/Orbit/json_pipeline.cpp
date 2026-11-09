#include "json_pipeline.h"
#include "hardware_action.h"
#include <ArduinoJson.h>

void setupJsonPipeline() {
  Serial.println("[JsonPipeline] 수신 파이프라인 준비 완료 (시리얼 입력 대기 중...)");
}

bool parseAndExecuteJson(const String& jsonPayload) {
  if (jsonPayload.length() == 0) return false;

  #if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument filter;
    JsonDocument doc;
  #else
    StaticJsonDocument<128> filter;
    StaticJsonDocument<256> doc;
  #endif
  // 백엔드 명령 + AI 응답 공통으로 필요한 필드만 남김 (AI 응답의 speech/latency 등으로 메모리 초과 방지)
  filter["stage"] = true;
  filter["led"] = true;
  filter["vibe"] = true;
  filter["oled"] = true;
  filter["oled_expression"] = true;

  DeserializationError error =
      deserializeJson(doc, jsonPayload, DeserializationOption::Filter(filter));
  if (error) {
    Serial.printf("[JsonPipeline] JSON 파싱 실패: %s | 입력값: %s\n", error.c_str(), jsonPayload.c_str());
    return false;
  }

  int stage   = doc["stage"].is<int>() ? doc["stage"].as<int>() : 0;   // null/없음 -> 0 (무시됨)
  String led  = doc["led"].is<const char*>()  ? doc["led"].as<String>()  : "";
  String vibe = doc["vibe"].is<const char*>() ? doc["vibe"].as<String>() : "";
  String oled = "";
  if (doc["oled"].is<const char*>())                 oled = doc["oled"].as<String>();             // 백엔드 명령
  else if (doc["oled_expression"].is<const char*>()) oled = doc["oled_expression"].as<String>();  // AI 응답

  // 일괄 적용
  applyHardwareAction(led, oled, vibe, stage);
  return true;
}

void processJsonPipeline() {
  static String inputBuffer = "";

  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) {
        Serial.printf("\n[Serial RX] 수신완료: %s\n", inputBuffer.c_str());
        parseAndExecuteJson(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += c;
    }
  }
}