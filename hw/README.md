# Orbit HW (ESP32 펌웨어)

키링형 인터랙티브 AI 디바이스 \*\*오빗(Orbit)\*\*의 ESP32 펌웨어입니다.
터치·흔들기·걸음 수를 감지해 MQTT로 서버에 보내고, 서버 명령을 받아 OLED 표정·LED·진동으로 반응합니다.

```
\[ESP32 키링] ⇄ MQTT 브로커 ⇄ \[백엔드 Spring Boot/MySQL] ⇄ \[AI 서버 FastAPI/Gemini]
```

\---

## 1\. 개발 환경

|항목|값|
|-|-|
|보드|DOIT ESP32 DEVKIT V1|
|IDE|Arduino IDE (보드 매니저: **esp32 by Espressif Systems**)|
|시리얼 속도|115200 baud, 줄 끝 `Newline`|

## 2\. 설치할 라이브러리

Arduino IDE → 라이브러리 매니저에서 설치합니다.

|라이브러리|용도|비고|
|-|-|-|
|**PubSubClient** (Nick O'Leary)|MQTT 통신|2.8 이상 (cleanSession 인자가 있는 `connect()` 사용)|
|**ArduinoJson** (Benoit Blanchon)|명령·상태 JSON 처리|v6 / v7 모두 동작하도록 작성|
|**U8g2** (olikraus)|SH1106 OLED 표정||
|**Adafruit NeoPixel**|WS2812B LED||

ESP32 코어에 포함되어 별도 설치가 필요 없는 것: `WiFi`, `Wire`, `Preferences`(NVS), `time.h`(NTP)

## 3\. 부품 및 핀 배치

|부품|모델|ESP32 핀|비고|
|-|-|-|-|
|OLED|SH1106 128×64 (I2C)|SDA 21 / SCL 22|MPU6050과 I2C 버스 공유|
|6축 센서|MPU6050 (I2C, 0x68)|SDA 21 / SCL 22|가속도 ±4g, 자이로 ±500°/s|
|LED|NeoPixel (WS2812B) 1개|GPIO 18|`Orbit.ino` `LED\_PIN`|
|터치 센서|TTP223 (디지털)|GPIO 14|딥슬립 깨우기(EXT0)도 같은 핀|
|진동 모터|PP-A811|GPIO 12|`non\_blocking\_hw.h` `VIBE\_PIN`|
|마이크|INMP441 (I2S)|미정|개발 예정|
|앰프+스피커|MAX98357A (I2S)|미정|개발 예정|
|광센서|미정|미정|개발 예정|
|충전 모듈|TP4056 (USB-C)|-|기본 충전 약 1A, PROG 저항 조정 필요|
|배터리|LiPo 약 520mAh (JST)|-|승압 모듈 없음 (전원부 검토 중)|

## 4\. 설정 (`config.h`)

|항목|기본값|설명|
|-|-|-|
|`WIFI\_SSID` / `WIFI\_PASSWORD`|-|Wi-Fi 정보 (2.4GHz만 지원)|
|`MQTT\_SERVER\_IP` / `MQTT\_PORT`|- / 1883|브로커 주소|
|`DEVICE\_ID\_OVERRIDE`|`"ORBIT-001"`|주석 처리하면 MAC 주소를 deviceId로 사용|
|`SLEEP\_TIMEOUT\_MS`|120000|무활동 시 딥슬립까지 시간 (2분)|
|`SHAKE\_STILL\_MS`|3000|마지막 걸음 후 이 시간 이상 정지해야 SHAKE 인정|
|`STATUS\_HEARTBEAT\_MS`|10000|상태 JSON 발행 주기|
|`WIFI\_REBEGIN\_MS`|15000|Wi-Fi가 이 시간 이상 끊기면 직접 재접속|
|`MQTT\_PERSISTENT\_SESSION`|0|1이면 cleanSession=false + QoS1 구독 (미적용)|

## 5\. 파일 구성

|파일|역할|
|-|-|
|`Orbit.ino`|진입점. 초기화 순서, 메인 루프(이벤트 → 반응·발행), 상태 JSON 주기 발행|
|`config.h`|Wi-Fi·MQTT·타이머 등 설정값|
|`mqtt\_manager`|MQTT 접속·재접속(지수 백오프), Wi-Fi 끊김 감시·재접속, 발행/구독|
|`json\_pipeline`|수신 JSON 파싱(MQTT 명령 + 시리얼 입력). 백엔드 `oled`, AI `oled\_expression` 모두 처리|
|`hardware\_action`|명령 값(led/vibe/oled/stage)을 실제 동작으로 변환. 표정 자동 복귀 타이머|
|`non\_blocking\_hw`|LED 효과(숨쉬기·페이드·무지개)와 진동 패턴을 `delay()` 없이 실행|
|`event\_detector`|터치·길게 누름·흔들기·걸음 이벤트 판정, 슬립 타이머 갱신|
|`motion`|MPU6050 초기화·영점 보정, 흔들기 감지, 만보기. 걸음 수와 보정값을 RTC 메모리에 저장|
|`time\_sync`|NTP(KST) 시각 동기화, 날짜가 바뀌면 걸음 수 초기화|
|`stage\_manager`|성장 단계(0\~4)와 단계별 테마색. NVS에 저장해 전원이 꺼져도 유지|
|`status\_builder`|발행용 이벤트 문자열·상태 JSON 생성|
|`OrbitFace`|SH1106 OLED 표정 그리기, 눈 깜빡임, 기상·수면 애니메이션|
|`OrbitLED`|NeoPixel 저수준 제어|
|`TouchHandler`|TTP223 터치 상태와 누른 시간 측정|
|`OrbitSleep`|무활동 타임아웃 시 딥슬립 진입(터치로 기상), 진입 직전 상태 발행|

## 6\. 통신 규격 (MQTT)

### 발행: `orbit/{deviceId}/status`

|payload|조건|
|-|-|
|`TOUCH\_LONG`|터치 1.5초 이상|
|`SHAKE`|마지막 걸음 후 3초 정지 상태에서 흔들기|
|`{"stage":1,"steps":120,"mqtt":"connected","uptime":3600}`|MQTT 접속 직후 1회 + 10초마다 + 딥슬립 직전|

### 구독: `orbit/{deviceId}/command`

```json
{"stage": 2, "led": "rainbow", "vibe": "strong\_double", "oled": "EXPR\_HAPPY"}
```

모든 필드는 선택 사항입니다. 대소문자는 구분하지 않으며 `EXPR\_` 접두어는 있어도 되고 없어도 됩니다.

|필드|지원 값|
|-|-|
|`oled` (또는 `oled\_expression`)|`happy`, `sad`, `calm`/`normal`/`idle\_eyes`, `angry`(임시로 dizzy), `dizzy`, `listening`, `thinking`, `sleep`|
|`led`|`rainbow`, `blue`/`dim\_blue`, `purple`, `yellow`, `pink`, `orange`, `lime`, `green`, `skyblue`|
|`vibe`|`short`/`short\_pulse`, `long`/`soft\_continuous`, `double`/`strong\_double`, `none`|
|`stage`|1\~4 (0이나 null이면 무시)|

미구현: 진동 `calm\_wave`, `two\_short\_taps`

## 7\. 동작 요약

|입력|키링 반응|서버 전송|
|-|-|-|
|터치|웃는 표정 + 노란빛 + 두 번 진동 (손 떼면 복귀)|-|
|터치 1.5초 이상|(위와 동일)|`TOUCH\_LONG`|
|흔들기|어지러운 표정 2초 + 보라빛|`SHAKE`|
|걷기|걸음 수 누적 (자정에 초기화)|상태 JSON의 `steps`|
|2분 무활동|잠드는 애니메이션 후 딥슬립|상태 JSON 1회|
|평상시|현재 Stage 테마색 숨쉬기|10초마다 상태 JSON|

## 8\. 테스트 (네트워크 없이)

시리얼 모니터(115200, Newline)에 JSON을 한 줄 보내면 MQTT 명령과 똑같이 처리됩니다.

```
{"oled":"happy","vibe":"short"}
{"oled\_expression":"EXPR\_SAD","led":"blue","vibe":"soft\_continuous"}
{"led":"rainbow","vibe":"strong\_double","oled\_expression":"EXPR\_HAPPY"}
{"stage":3}
```

