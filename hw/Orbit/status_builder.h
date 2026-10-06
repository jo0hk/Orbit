#ifndef STATUS_BUILDER_H
#define STATUS_BUILDER_H

#include <Arduino.h>

// 백엔드 합의 규격: {"event":"TOUCH_LONG","stepCount":150}
String buildEventJson(const char* event, int stepCount);

// config.h의 STATUS_PAYLOAD_JSON에 따라 JSON 또는 호환 문자열을 반환
// 호환 모드에서 백엔드 미지원 이벤트이면 빈 문자열 반환 (발행하지 말 것)
String buildEventPayload(const char* event, int stepCount);

// 디버그/하트비트용 (백엔드 규격 아님)
String buildStatusJson(int currentStage, int currentSteps, bool mqttConnected);

#endif