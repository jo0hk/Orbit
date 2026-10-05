#include "json_pipeline.h"
#include "hardware_action.h"
#include <ArduinoJson.h>

void setupJsonPipeline() {
  Serial.println("[JsonPipeline] 수신 파이프라인 준비 완료 (시리얼 입력 대기 중...)");
}

bool parseAndExecuteJson(const String& jsonPayload) {
  if (jsonPayload.length() == 0) return false;

  // 버퍼 크기를 1024로 확장하여 모든 필드 수신에 충분하도록 설정
  #if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
  #else
    StaticJsonDocument<1024> doc;
  #endif

  DeserializationError error = deserializeJson(doc, jsonPayload);

  if (error) {
    Serial.printf("[JsonPipeline ❌] JSON 파싱 실패: %s | 입력값: %s\n", error.c_str(), jsonPayload.c_str());
    return false;
  }

  // 안전한 필드 읽기
  int stage   = doc["stage"].is<int>() ? doc["stage"].as<int>() : 0;
  String oled = doc["oled"].is<const char*>() ? doc["oled"].as<String>() : "";
  String led  = doc["led"].is<const char*>()  ? doc["led"].as<String>()  : "";
  String vibe = doc["vibe"].is<const char*>() ? doc["vibe"].as<String>() : "";

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