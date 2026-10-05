#ifndef JSON_PIPELINE_H
#define JSON_PIPELINE_H

#include <Arduino.h>

void setupJsonPipeline();
void processJsonPipeline(); // loop()에서 호출하여 시리얼 JSON 입력 및 파싱 처리

// JSON 문자열 패킷을 전달받아 파싱 후 applyHardwareAction 실행하는 함수
bool parseAndExecuteJson(const String& jsonPayload);

#endif