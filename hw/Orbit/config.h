#ifndef CONFIG_H
#define CONFIG_H

#define WIFI_SSID             "wifi_name"
#define WIFI_PASSWORD         "wifi_password"

// --- MQTT 브로커 설정 ---
#define MQTT_SERVER_IP        "ipv4"
#define MQTT_PORT             1883
// 계정이 필요하면 아래 두 줄 주석 해제
// #define MQTT_USER          "user"
// #define MQTT_PASSWORD      "password"
#define MQTT_RETRY_INIT_MS    2000
#define MQTT_RETRY_MAX_MS     60000

// --- 디바이스 설정 ---
// 연동 테스트용 고정 ID. 주석 처리하면 MAC 주소를 deviceId로 사용
#define DEVICE_ID_OVERRIDE    "ORBIT-001"

// --- 타이머 / 이벤트 상수 ---
#define SLEEP_TIMEOUT_MS      30000
// SHAKE는 마지막 걸음 이후 이 시간 이상 정지한 상태에서만 인정 (백엔드 규격: 3초 정지 후 흔들림)
#define SHAKE_STILL_MS        3000

// status payload 형식
//  1: JSON  {"event":"TOUCH_LONG","stepCount":150}   (백엔드가 JSON 파싱을 지원할 때)
//  0: 문자열 호환 모드  TOUCH_LONG -> "TOUCHED"       (백엔드가 문자열만 처리하는 현재 상태)
//     호환 모드에서는 백엔드 미지원 이벤트(SHAKE, STEP_TICK)는 발행하지 않음
#define STATUS_PAYLOAD_JSON   0

// STEP_TICK 발행 (백엔드 확인 전까지 비활성). 켜면 STEP_TICK_BATCH 걸음마다 1회 발행
#define STEP_TICK_PUBLISH_ENABLED  0
#define STEP_TICK_BATCH            10

#endif