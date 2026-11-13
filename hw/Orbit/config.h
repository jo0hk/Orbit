#ifndef CONFIG_H
#define CONFIG_H

#define WIFI_SSID             "kys"
#define WIFI_PASSWORD         "06120814"

// --- MQTT 브로커 설정 ---
#define MQTT_SERVER_IP        "mqtt_ip"
#define MQTT_PORT             1883

// 계정이 필요하면 아래 두 줄 주석 해제
// #define MQTT_USER          "user"
// #define MQTT_PASSWORD      "password"
#define MQTT_RETRY_INIT_MS    2000
#define MQTT_RETRY_MAX_MS     60000

#define WIFI_REBEGIN_MS          15000   // Wi-Fi 끊기면 직접 재접속
#define MQTT_PERSISTENT_SESSION  0       // 1: cleanSession=false + QoS1 구독 (⑥)

// --- 디바이스 설정 ---
// 연동 테스트용 고정 ID. 주석 처리하면 MAC 주소를 deviceId로 사용
#define DEVICE_ID_OVERRIDE    "ORBIT-001"

// --- 타이머 / 이벤트 상수 ---
#define SLEEP_TIMEOUT_MS      120000
// SHAKE는 마지막 걸음 이후 이 시간 이상 정지한 상태에서만 인정 (백엔드 규격: 3초 정지 후 흔들림)
#define SHAKE_STILL_MS        3000

// status payload 형식
//  0: 문자열 모드  TOUCH_LONG / SHAKE / STEP_TICK 이름 그대로 발행 (현재 백엔드 형식)
#define STATUS_PAYLOAD_JSON   0
#define STATUS_HEARTBEAT_ENABLED   1
#define STATUS_HEARTBEAT_MS        10000

// STEP_TICK 발행 (백엔드 확인 전까지 비활성). 켜면 STEP_TICK_BATCH 걸음마다 1회 발행
#define STEP_TICK_PUBLISH_ENABLED  0
#define STEP_TICK_BATCH            10

// --- AI 서버 (키링 음성 교신: POST /api/v1/interact/voice) ---
#define AI_SERVER_HOST        "ai_server_ip"
#define AI_SERVER_PORT        8000
#define AI_HTTP_TIMEOUT_MS    20000   // STT+LLM+TTS 대기. AI 실측값 받으면 조정

// --- 오디오 / 광센서 핀 ---
#define MIC_SCK_PIN           32      // INMP441 (VDD 3.3V, L/R=GND)
#define MIC_WS_PIN            13
#define MIC_SD_PIN            33
#define SPK_BCLK_PIN          26      // MAX98357A
#define SPK_LRC_PIN           25
#define SPK_DIN_PIN           27
#define LIGHT_PIN             34      // CdS 분압 (ADC1 필수: Wi-Fi 사용 중 ADC2 불가)
#define LIGHT_R_FIXED_OHM     10000.0f

// --- 녹음 ---
#define REC_SAMPLE_RATE       16000   // 16kHz 16bit 모노 WAV
#define REC_MIC_SHIFT         14      // 32bit -> 16bit 변환 (작을수록 소리 큼)
#define REC_NOISE_CAL_MS      300     // 녹음 직전 소음 측정
#define REC_SPEECH_FACTOR     3.0f    // 소음 RMS의 몇 배부터 말소리
#define REC_SPEECH_MIN_RMS    150.0f  // 말소리 시작 기준 하한 (유지 기준은 이 값의 절반)
#define REC_WAIT_SPEECH_MS    3000    // 시작 후 말이 없으면 취소
#define REC_SILENCE_END_MS    3000    // 말한 뒤 이만큼 조용하면 자동 종료 (더블탭으로 바로 종료 가능)
#define REC_MAX_MS            8000    // 최대 녹음 길이 (약 250KB)

// --- 더블탭 (음성 교신 시작/종료) ---
#define DOUBLE_TAP_MAX_PRESS_MS  300  // 이보다 짧게 누르면 '탭'
#define DOUBLE_TAP_GAP_MS        500  // 첫 탭을 뗀 뒤 이 시간 안에 두 번째 탭

#define PET_MIN_PRESS_MS         500  // 이 시간 이상 누르면 쓰다듬기 반응 (짧은 탭은 반응 없음)
#if PET_MIN_PRESS_MS <= DOUBLE_TAP_MAX_PRESS_MS
#error "PET_MIN_PRESS_MS는 DOUBLE_TAP_MAX_PRESS_MS보다 커야 더블탭과 겹치지 않음"
#endif

// --- 스피커 ---
#define AUDIO_TONE_VOLUME     0.3f
#define AUDIO_PLAY_VOLUME     0.8f    // 응답 음성 볼륨 (0~1)
#define AUDIO_STREAM_TIMEOUT_MS 3000  // 응답 음성 수신이 이만큼 끊기면 재생 중단

#endif