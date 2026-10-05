#ifndef CONFIG_H
#define CONFIG_H

// --- Wi-Fi & 네트워크 설정 ---
#define WIFI_SSID             "와이파이이름"
#define WIFI_PASSWORD         "와이파이비밀번호"

// --- MQTT 브로커 설정 ---
#define MQTT_SERVER_IP        "192.168.0.x"
#define MQTT_PORT             1883
#define MQTT_RETRY_INIT_MS    2000
#define MQTT_RETRY_MAX_MS     60000

// --- 디바이스 설정 ---
// 특정 고유 ID로 고정하려면 아래 문주를 해제하세요 (기본값: MAC 주소 자동)
// #define DEVICE_ID_OVERRIDE  "ORBIT_ROBOT_01"

// --- 하드웨어 핀 및 타이머 상수 ---
#define SLEEP_TIMEOUT_MS      30000

#endif