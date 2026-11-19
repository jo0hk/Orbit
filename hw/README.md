# Orbit HW (ESP32 펌웨어)

키링형 인터랙티브 AI 디바이스 오빗(Orbit)의 ESP32 펌웨어입니다.
터치·흔들기·걸음 수를 감지해 MQTT로 서버에 보내고, 서버 명령을 받아 OLED 표정·LED·진동으로 반응합니다.
더블탭하면 음성으로 AI와 교신합니다 (키링 → AI 서버 직접).

```
[ESP32 키링] ⇄ MQTT 브로커 ⇄ [백엔드 Spring Boot/MySQL] ⇄ [AI 서버 FastAPI/Gemini]
      └──────── HTTP (음성 교신) ────────────────────────────────┘
```

---

## 1. 개발 환경

|항목|값|
|-|-|
|보드|DOIT ESP32 DEVKIT V1|
|IDE|Arduino IDE (보드 매니저: **esp32 by Espressif Systems 3.x**, 3.3.12에서 확인)|
|파티션|Default 4MB with spiffs (LittleFS 녹음 파일용 영역 필요)|
|시리얼 속도|115200 baud, 줄 끝 `Newline`|

## 2. 설치할 라이브러리

Arduino IDE → 라이브러리 매니저에서 설치합니다.

|라이브러리|용도|비고|
|-|-|-|
|**PubSubClient** (Nick O'Leary)|MQTT 통신|2.8 이상 (cleanSession 인자가 있는 `connect()` 사용)|
|**ArduinoJson** (Benoit Blanchon)|명령·상태·AI 응답 JSON 처리|v6 / v7 모두 동작하도록 작성|
|**U8g2** (olikraus)|SH1106 OLED 표정||
|**Adafruit NeoPixel**|WS2812B LED||

ESP32 코어에 포함되어 별도 설치가 필요 없는 것: `WiFi`, `HTTPClient`, `Wire`, `Preferences`(NVS), `LittleFS`, `driver/i2s.h`, `driver/adc.h`, `time.h`(NTP)

> 마이크·스피커는 예전 방식 I2S 드라이버(`driver/i2s.h`)를 씁니다. 그래서 광센서도 예전 방식 ADC(`adc1_get_raw`)를 씁니다. `analogRead()`를 쓰면 부팅 시 `ADC: CONFLICT` 오류로 멈춥니다.

## 3. 부품 및 핀 배치

|부품|모델|ESP32 핀|비고|
|-|-|-|-|
|OLED|SH1106 128×64 (I2C)|SDA 21 / SCL 22|MPU와 I2C 버스 공유|
|6축 센서|MPU6050 호환 칩 (I2C 0x68, WHO_AM_I 0x72)|SDA 21 / SCL 22|가속도 ±4g, 자이로 ±500°/s. 축별 영점 보정값은 `config.h`|
|LED|NeoPixel (WS2812B) 1개|GPIO 18|5V|
|터치 센서|TTP223 (디지털)|GPIO 14|딥슬립 깨우기(EXT0)도 같은 핀|
|진동 모터|PP-A811|GPIO 12|부팅 시 LOW여야 하는 핀(strapping). 슬립 중 LOW 고정|
|마이크|INMP441 (I2S)|SCK 32 / WS 13 / SD 33|**VDD 3.3V**, L/R → GND|
|앰프|MAX98357A (I2S)|BCLK 26 / LRC 25 / DIN 27|**VIN 5V**, GAIN·SD 비움(9dB). 스피커는 앰프 단자에만 연결|
|스피커|소형 8Ω|앰프 +/− 단자|1W 이상 권장. 작은 스피커면 `AUDIO_PLAY_GAIN` 1.0~1.5|
|광센서|CdS + 10kΩ|GPIO 34|3.3V ─ CdS ─┬─ GPIO34, └─ 10kΩ ─ GND. ADC1만 사용 가능 (ADC2는 Wi-Fi와 충돌)|
|전원|USB 5V (보조배터리)|-|LiPo 내장형은 향후 과제|

> 배선을 바꾼 직후 첫 전원은 PC USB로 확인하세요. 보조배터리는 전류 제한이 없어 합선 시 부품이 과열될 수 있습니다.

## 4. 설정 (`config.h`)

> `config.h`에는 Wi-Fi 정보와 서버 IP가 들어가므로 **커밋하지 마세요.**

**네트워크**

|항목|기본값|설명|
|-|-|-|
|`WIFI_SSID` / `WIFI_PASSWORD`|-|Wi-Fi 정보 (2.4GHz만 지원)|
|`MQTT_SERVER_IP` / `MQTT_PORT`|- / 1883|브로커 주소. IP로 넣을 것 (이름이면 DNS 조회 대기)|
|`MQTT_RETRY_INIT_MS` / `MAX_MS`|2000 / 60000|접속 실패 시 재시도 간격 (2배씩 증가)|
|`WIFI_REBEGIN_MS`|15000|Wi-Fi가 이 시간 이상 끊기면 직접 재접속|
|`MQTT_PERSISTENT_SESSION`|0|1이면 cleanSession=false + QoS1 구독 (미적용)|
|`AI_SERVER_HOST` / `PORT`|- / 8000|AI 서버 주소 (음성 교신)|
|`AI_HTTP_TIMEOUT_MS`|30000|AI 응답 대기 (STT+LLM+TTS)|
|`DEVICE_ID_OVERRIDE`|`"ORBIT-001"`|주석 처리하면 MAC 주소를 deviceId로 사용|

**동작**

|항목|기본값|설명|
|-|-|-|
|`SLEEP_TIMEOUT_MS`|120000|무활동 시 딥슬립까지 시간 (2분)|
|`SHAKE_STILL_MS`|3000|마지막 걸음 후 이 시간 이상 정지해야 SHAKE 인정|
|`ACC_OFFSET_X/Y/Z_G`|−0.82 / 0.51 / −0.28|MPU 축별 영점 (6방향 실측). **모듈을 바꾸면 다시 측정**|
|`STATUS_HEARTBEAT_MS`|10000|상태 JSON 발행 주기|
|`STEP_TICK_PUBLISH_ENABLED`|0|걸음 묶음 발행 (미사용)|
|`PET_MIN_PRESS_MS`|500|이 시간 이상 누르면 쓰다듬기 반응|
|`DOUBLE_TAP_MAX_PRESS_MS` / `GAP_MS`|300 / 500|더블탭 판정|

**음성·센서**

|항목|기본값|설명|
|-|-|-|
|`REC_*`|-|녹음 설정 (16kHz, 말소리 감지, 3초 침묵 시 종료, 최대 8초)|
|`VOICE_READY_WAIT_MS`|15000|부팅·기상 후 Wi-Fi가 붙으면 준비음 (이 시간 넘으면 생략)|
|`VOICE_WIFI_WAIT_MS`|5000|더블탭 시 Wi-Fi가 없으면 이만큼 기다린 뒤 시작|
|`AUDIO_PLAY_GAIN`|2.0|응답 음성 증폭 배율 (넘치는 부분은 잘림)|
|`AUDIO_TONE_VOLUME`|0.3|효과음 볼륨|
|`LIGHT_SEND_ENABLED`|1|0이면 음성 요청에 조도(lux)를 보내지 않음|
|`LIGHT_R_FIXED_OHM`|10000|광센서 분압 저항|

## 5. 파일 구성

|파일|역할|
|-|-|
|`Orbit.ino`|진입점. 초기화 순서, 메인 루프(이벤트 → 반응·발행), 상태 JSON 주기 발행|
|`config.h`|Wi-Fi·MQTT·AI 서버·타이머·핀 등 설정값|
|`mqtt_manager`|MQTT 발행/구독, Wi-Fi 끊김 감시·재접속. **접속 시도는 별도 태스크**에서 해서 서버가 응답하지 않아도 loop가 멈추지 않음|
|`json_pipeline`|수신 JSON 파싱(MQTT 명령 + AI 응답 + 시리얼 입력). 백엔드 `oled`, AI `oled_expression` 모두 처리|
|`hardware_action`|명령 값(led/vibe/oled/stage)을 실제 동작으로 변환. 표정 자동 복귀 타이머|
|`non_blocking_hw`|LED 효과(숨쉬기·페이드·무지개)와 진동 패턴을 `delay()` 없이 실행|
|`event_detector`|터치·더블탭·길게 누름·흔들기·걸음 이벤트 판정, 슬립 타이머 갱신|
|`motion`|MPU 초기화, 축별 영점 보정, 흔들기 감지, 만보기(연속 4걸음부터 인정). 걸음 수는 RTC 메모리에 저장|
|`time_sync`|NTP(KST) 시각 동기화, 날짜가 바뀌면 걸음 수 초기화|
|`stage_manager`|성장 단계(0~4)와 단계별 테마색. NVS에 저장해 전원이 꺼져도 유지|
|`status_builder`|발행용 이벤트 문자열·상태 JSON 생성|
|`voice_client`|음성 교신 전체 흐름 (별도 태스크). 녹음 → AI 업로드 → 응답 적용 → 음성 재생, 실패 시 재시도·비상 응답|
|`audio_in`|INMP441 녹음, 말소리 감지(VAD), LittleFS에 WAV 저장|
|`audio_out`|MAX98357A 재생 (효과음, 응답 WAV 스트리밍, 펌웨어 내장 음성). 16kHz만 재생|
|`light_sensor`|CdS 조도 측정 (0~1000 lux 근사, 실측 51 lux @ 2150mV로 보정)|
|`emergency_voice.h`|비상 음성 데이터 (16kHz 모노 PCM 배열). 없으면 효과음으로 대신함|
|`OrbitFace`|SH1106 OLED 표정 엔진. 평상시 깜빡임·시선 이동, 표정 간 부드러운 전환, 기상·수면 애니메이션|
|`OrbitLED`|NeoPixel 저수준 제어|
|`TouchHandler`|TTP223 터치 상태와 누른 시간 측정|
|`OrbitSleep`|무활동 타임아웃 시 딥슬립 진입(터치로 기상). 진입 직전 상태 발행, I2S·진동 핀 LOW 고정|

## 6. 통신 규격

### 6-1. MQTT 발행: `orbit/{deviceId}/status`

|payload|조건|
|-|-|
|`TOUCH_LONG`|터치 1.5초 이상|
|`SHAKE`|마지막 걸음 후 3초 정지 상태에서 흔들기|
|`{"stage":1,"steps":120,"mqtt":"connected","uptime":3600}`|MQTT 접속 직후 1회 + 10초마다 + 딥슬립 직전|

### 6-2. MQTT 구독: `orbit/{deviceId}/command`

```json
{"stage": 2, "led": "rainbow", "vibe": "strong_double", "oled": "EXPR_HAPPY"}
```

모든 필드는 선택 사항입니다. 대소문자는 구분하지 않으며 `EXPR_` 접두어는 있어도 되고 없어도 됩니다.

|필드|지원 값|
|-|-|
|`oled` (또는 `oled_expression`)|`happy`, `sad`, `normal`/`idle_eyes`, `calm`, `angry`, `dizzy`, `listening`, `thinking`, `sleep`|
|`led`|`rainbow`, `blue`/`dim_blue`, `purple`, `yellow`, 단계색 `skyblue`(0) `teal`(1) `mint`(2) `orange`(3) `pink`(4)|
|`vibe`|`short`/`short_pulse`, `long`/`soft_continuous`, `double`/`strong_double`, `two_short_taps`, `calm_wave`, `none`|
|`stage`|1~4 (0이나 null이면 무시)|

**단계 테마색**

|단계|이름|RGB|
|-|-|-|
|0 (미동기화)|skyblue|135, 206, 250|
|1|teal 청록|0, 200, 180|
|2|mint 민트|0, 255, 60|
|3|orange 주황|255, 150, 0|
|4|pink 핑크|255, 90, 70|

### 6-3. 음성 교신: `POST /api/v1/interact/voice` (키링 → AI 서버)

- 요청 (multipart): `audio`(16kHz 16bit 모노 WAV), `device_id`, `lux`(선택), `request_id`
- 응답 JSON의 `led` / `vibe` / `oled_expression`을 바로 적용하고, `audio_url`의 WAV(16kHz)를 받아 재생
- 연결·전송 실패, 서버 5xx면 같은 `request_id`로 1회 재시도 (시간 초과는 재시도 안 함)

## 7. 동작 요약

|입력|키링 반응|서버 전송|
|-|-|-|
|터치 0.5초 이상|웃는 표정 + 노란빛 + 두 번 진동 (손 떼면 복귀)|-|
|터치 1.5초 이상|(위와 동일)|`TOUCH_LONG`|
|**더블탭**|음성 교신 시작 (아래 참고). 녹음·재생 중 더블탭은 종료|AI 서버|
|흔들기|어지러운 표정 2초 + 보라빛|`SHAKE`|
|걷기|걸음 수 누적 (연속 4걸음부터, 자정에 초기화)|상태 JSON의 `steps`|
|2분 무활동|잠드는 애니메이션 후 딥슬립|상태 JSON 1회|
|터치로 기상|눈뜨는 애니메이션, Wi-Fi 연결되면 준비음 "띠-링"|-|
|평상시|현재 단계 테마색 숨쉬기, 깜빡임·시선 이동|10초마다 상태 JSON|

**음성 교신 흐름**

1. 더블탭 → 시작음 → LISTENING 표정, 녹음
2. 말이 끝나고 3초 조용하면 자동 종료 (더블탭으로 바로 종료 가능, 최대 8초)
3. THINKING 표정 → AI 서버로 업로드 (조도 함께 전송)
4. 응답 표정·LED·진동 적용 → 응답 음성 재생
5. 실패 시

|실패|반응|
|-|-|
|말이 없음|기본 표정, 짧은 효과음|
|녹음 오류|슬픈 표정 + 짧은 진동 + 실패음|
|AI 서버에 닿지 못함 (Wi-Fi·연결·시간 초과·5xx·응답 오류)|**비상 응답**: 슬픈 표정 + 파란 LED + 짧은 진동 + 비상 음성|
|Gemini만 실패|AI 서버가 보낸 비상 대사(`fallback_triggered`)를 정상 재생|

## 8. 비상 음성 교체

`emergency_voice.h`가 폴더에 있으면 자동으로 쓰이고, 없으면 효과음으로 대신합니다. 현재는 임시 효과음(무전 잡음 + 삐삐삐)이 들어 있습니다.

AI 담당에게 받은 WAV(16kHz / 모노 / 16bit)를 아래 스크립트로 변환해 덮어쓰면 됩니다. 코드 수정은 필요 없습니다.

```
python wav_to_header.py emergency.wav   → emergency_voice.h 생성 → hw/Orbit에 덮어쓰기
```

<details>
<summary>wav_to_header.py</summary>

```python
import sys, wave, array

src = sys.argv[1]
w = wave.open(src, "rb")
if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
    sys.exit(f"형식 다름: {w.getframerate()}Hz, {w.getnchannels()}ch, {w.getsampwidth()*8}bit "
             "-> 16000Hz, 1ch, 16bit 필요")

pcm = array.array("h", w.readframes(w.getnframes()))
peak = max(abs(s) for s in pcm) if pcm else 0
print(f"길이 {len(pcm)/16000:.2f}초, 크기 {len(pcm)*2/1024:.0f}KB, 최대 음량 {peak}/32767")
if peak > 16000:
    print("주의: 키링이 2.0배 키우므로 찌그러질 수 있음 (config.h AUDIO_PLAY_GAIN 1.5 이하 권장)")

with open("emergency_voice.h", "w", encoding="utf-8") as f:
    f.write("// 비상 음성 (16kHz 모노 PCM16). wav_to_header.py로 생성\n#pragma once\n#include <stdint.h>\n#include <stddef.h>\n\n")
    f.write("static const int16_t EMERGENCY_PCM[] = {\n")
    for i in range(0, len(pcm), 16):
        f.write("  " + ", ".join(str(s) for s in pcm[i:i+16]) + ",\n")
    f.write("};\nstatic const size_t EMERGENCY_PCM_LEN = sizeof(EMERGENCY_PCM) / sizeof(EMERGENCY_PCM[0]);\n")
print("emergency_voice.h 생성 완료")
```

</details>

## 9. 테스트 (네트워크 없이)

시리얼 모니터(115200, Newline)에 JSON을 한 줄 보내면 MQTT 명령과 똑같이 처리됩니다.

```
{"oled":"happy","vibe":"short"}
{"oled_expression":"EXPR_SAD","led":"blue","vibe":"soft_continuous"}
{"led":"rainbow","vibe":"strong_double","oled_expression":"EXPR_HAPPY"}
{"stage":3}
{"vibe":"calm_wave"}
{"vibe":"two_short_taps"}
```

**진단 로그**

|로그|의미|
|-|-|
|`[Motion] 센서 오프셋 보정 완료 (측정: X.XXg ...)`|부팅 시 정지 상태면 1.00g 근처가 정상|
|`[Voice] 응답 200 (N ms)`|AI 응답 시간|
|`[Mem] 힙 여유 ... / 최소 ...`|교신마다 출력. 최소 힙이 계속 줄면 메모리 누수|
|`[AudioOut] 원본 최대 음량 N / 32767`|16000 이상이면 증폭 시 찌그러짐|
|`[Light] N mV -> 약 N lux`|조도 측정값|
|`[Face] 5초 통계 ...`|`OrbitFace.cpp`의 `FACE_STATS_ENABLED 1`일 때. loop 최대 간격 평상시 약 35ms|

## 10. 알려진 제한

- 녹음 중에는 플래시 쓰기 때문에 loop가 최대 약 160ms 밀립니다. 아주 짧은 탭을 놓칠 수 있습니다.
- 광센서는 10kΩ 기준 약 250 lux 이상에서 포화됩니다 (AI는 50 lux 이하 여부만 사용하므로 문제없음).
- 응답 음성은 16kHz WAV만 재생합니다 (다른 샘플레이트는 무음).
- 보조배터리 전원일 때, 딥슬립 중 전류가 적어 보조배터리가 자동으로 꺼질 수 있습니다.
