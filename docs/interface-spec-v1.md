# 인터페이스 정의서 v1 (2학기 1주차)

> 작성: AI/PM · 2026-09-21
> 대상: HW · 앱 · 백엔드 · AI 전 파트
> 근거: `backend/` 실제 코드(커밋 `0fad53a`)와 `ai/app/schemas.py` 대조

---

## 0. 요약 — 합의가 필요한 5건

| # | 항목 | 현재 상태 | 제안 |
| --- | --- | --- | --- |
| 1 | AI 서버 호출 주체 | 백엔드가 자체 Gemini 호출 예정 | 백엔드 → AI 서버 호출로 일원화 |
| 2 | 감정 라벨 | 3곳이 서로 다름 | **사용자 감정**과 **오빗 상태**를 분리 |
| 3 | HW 제어값 | AI만 정의, 백엔드·HW 미정의 | AI enum을 기준으로 채택 |
| 4 | MQTT 이벤트 | 스탯 증가용 문자열 | 미션 판정용으로 확장 |
| 5 | `userId` 타입 | `Long` / `Integer` 혼용 | `Long`으로 통일 |

---

## 1. AI 서버 호출 경로 ⚠️ 최우선

### 현재 상태

백엔드 `WalkAiController`가 프롬프트를 조립한 뒤, AI 서버를 호출하지 않고 고정 문자열을 반환합니다.

```java
return Map.of(
    "prompt", prompt,
    "answer", "현재 위치와 날씨 정보를 바탕으로 산책 조언을 생성했습니다. 추후 Gemini API 응답으로 교체 예정입니다."
);
```

즉 백엔드는 **직접 Gemini를 호출할 계획**입니다. 그러면 AI 서버(`POST /api/v1/interact/voice`)를 아무도 부르지 않게 됩니다.

### 두 경로가 생기면 깨지는 것

`WalkAiService.createWalkPrompt()`의 프롬프트는 오빗 페르소나가 아닙니다.

> 너는 사용자의 산책 상황을 분석해서 조언해주는 AI야.

- `대장님` 호칭 없음, 무전 톤 없음, `치직-` / `오버` 없음
- Strict JSON 아님 → `led` / `vibe` / `oled_expression` 추출 불가
- 감정 분석 결과가 들어가지 않음 → 3주차 감정 엔진이 무의미해짐
- 45자 압축 규칙 없음 → 레이턴시 증가

이대로 가면 **앱에서 보이는 오빗이 두 인격**이 됩니다.

### 제안

```
앱 ──음성──▶ 백엔드(Spring Boot) ──HTTP──▶ AI 서버(FastAPI) ──▶ Gemini
                    │                           │
                    └── DB 저장                  └── STT / 감정분석 / TTS
```

- **Gemini 호출은 AI 서버만** 수행합니다. 백엔드는 Gemini SDK를 쓰지 않습니다.
- 백엔드는 대화 저장·조회, MQTT 수신, 미션 판정을 담당합니다.
- `WalkAiService`의 산책 데이터(거리·시간·위치·날씨)는 버리지 않고, AI 서버 요청의 `EnvContext`로 전달합니다.

### 요청 스펙

```
POST /api/v1/interact/voice        (multipart/form-data)
  audio        : 음성 파일 (필수)
  session_id   : string (필수)
  turn_no      : int
  lux          : int | null        조도
  weather      : string | null     "화창함" 등
  location     : string | null     비식별 위치
  distance_m   : int | null        GPS 누적 이동 거리
  duration_min : int | null        산책 시간
  mission_id   : string | null
  mission_result : success | fail | retry | none
```

### 응답 스펙

```json
{
  "speech": "치직- 대장님, 오늘 컨디션은 어떠십니까. 오버",
  "led": "dim_blue",
  "vibe": "soft_continuous",
  "oled_expression": "sad_eyes",
  "audio_url": "outputs/xxxx.mp3",
  "user_text": "오늘 좀 힘들었어",
  "stt_confidence": 0.91,
  "user_emotion": "sad",
  "user_emotion_confidence": 0.87,
  "latency": { "stt_ms": 0, "emotion_ms": 0, "llm_ms": 0, "tts_ms": 0, "total_ms": 0 },
  "llm_retry_count": 0,
  "fallback_triggered": false
}
```

백엔드는 이 응답을 그대로 DB에 저장하고(2주차 스키마 참조), `speech` / `led` / `vibe` / `oled_expression`을 앱·HW로 전달합니다.

---

## 2. 감정 라벨 ⚠️ 3곳 불일치

### 현재 상태

| 위치 | 값 | 비고 |
| --- | --- | --- |
| AI 감정 모델 (`.pth` label_encoder) | `sad` `anger` `fear` `disgust` `neutral` | 소문자 5클래스 |
| `CharacterStatus.emotionStatus` | `"NORMAL"` `"HAPPY"` `"SAD"` | 대문자, MQTT로 변경 |
| `MoodService.currentMood` | `"happy"` | 소문자, 인메모리 전역 변수 |

`HAPPY`는 **AI 모델에 존재하지 않는 라벨**입니다. 그대로 두면 백엔드가 AI에게 없는 값을 기대하게 됩니다.

### 원인 — 두 개념이 섞였습니다

- **사용자 감정** : 발화를 분석한 결과. AI가 판정. 매 턴 바뀜.
- **오빗 상태** : 캐릭터가 지금 어떤 기분인지. 누적 상호작용의 결과. 천천히 바뀜.

이름이 비슷해서 한 필드처럼 다뤄졌지만 **서로 다른 것**입니다. 분리하면 충돌이 사라집니다.

### 제안

| 개념 | 필드명 | 값 | 주인 |
| --- | --- | --- | --- |
| 사용자 감정 | `user_emotion` | `sad` `anger` `fear` `disgust` `neutral` | AI 서버 |
| 오빗 상태 | `orbit_mood` | `NORMAL` `HAPPY` `SAD` | 백엔드 |

**매핑 규칙** (백엔드가 적용)

| user_emotion | orbit_mood 변화 |
| --- | --- |
| `neutral` | 변화 없음 |
| `sad`, `fear` | `SAD` |
| `anger`, `disgust` | 변화 없음 (적대 발화에 오빗이 흔들리지 않음) |
| 미션 성공 이벤트 | `HAPPY` |

이렇게 하면 **AI 모델을 재학습하지 않고도** 미션 성공 시 오빗이 기뻐할 수 있습니다.
→ 1주차 쟁점이던 "긍정 라벨 부재"가 재학습 없이 해소됩니다.

### `MoodService` 정리 필요

```java
private String currentMood = "happy";   // 인메모리 전역 변수
```

사용자 구분이 없고 서버 재시작 시 사라집니다. `CharacterStatus.emotionStatus`와 역할이 겹치므로 **둘 중 하나로 통합**해야 합니다. `CharacterStatus` 쪽이 DB에 남고 `userId`가 있으므로 그쪽을 유지하고 `MoodService`를 폐기하는 안을 권합니다.

---

## 3. 하드웨어 제어값

`ai/app/schemas.py`의 enum이 기준입니다. 값 출처는 1학기 `ContextInjector` 프롬프트입니다.

| 조건 | `led` | `vibe` | `oled_expression` |
| --- | --- | --- | --- |
| 긍정/중립, 환경 양호 | `rainbow` | `strong_double` | `idle_eyes` |
| `sad` / `fear` / 조도 50 lux 이하 | `dim_blue` | `soft_continuous` | `sad_eyes` / `wide_eyes` |
| `anger` / `disgust` | `dim_white` | `calm_wave` | `wide_eyes` |
| 통신 장애 (비상 프로토콜) | `orange` | `short` | `sad_eyes` |
| 미션 성공 | `rainbow` | `strong_double` | `star_eyes` |

**HW 파트 확인 필요**
- 위 값을 ESP32-S3 펌웨어에서 어떻게 해석할지 정의되어 있는지
- `oled_expression`은 1학기 AI 파이프라인에 **구현되어 있지 않았습니다.** 현재는 서버가 감정에서 파생합니다(`schemas.oled_for()`). HW가 실제로 그릴 수 있는 표정 목록에 맞춰 조정이 필요합니다.

---

## 4. MQTT 이벤트

### 현재 상태 (`MqttMessageHandler`)

| payload | 동작 |
| --- | --- |
| `FUEL_UP` | 연료 +10 |
| `LOVE_UP` | 친밀도 +5 |
| `STAGE_UP` | 스테이지 +1 |
| `JACKPOT_SUCCESS` | 연료 +10, 친밀도 +5 |
| `EMOTION_HAPPY` / `EMOTION_SAD` | 감정 상태 변경 |
| `TOUCHED` | 감정 HAPPY, 친밀도 +5 |

### 문제

- **미션 판정이 아니라 스탯 증가**입니다. 4주차 미션 정의표(`m_touch_ack` 등)와 연결되지 않습니다.
- `charId = 1L` 하드코딩. 사용자 구분이 없습니다.
- 페이로드가 평문 문자열이라 **센서값(터치 횟수, lux, 가속도 크기)이 실리지 않습니다.** 5주차에 "2초 내 3회 터치" 같은 조건을 판정할 수 없습니다.

### 제안 — JSON 페이로드로 전환

```json
{ "type": "TOUCH", "user_id": 1, "value": 1, "ts": 1758387600000 }
{ "type": "LUX",   "user_id": 1, "value": 15, "ts": 1758387600000 }
{ "type": "ACCEL", "user_id": 1, "value": 2.4, "ts": 1758387600000 }
```

기존 문자열 이벤트는 유지하되, 미션 판정용 채널을 별도로 둬도 됩니다. 4주차 미션 정의표의 성공 조건이 전부 **임계값 + 시간창** 형태라 값과 타임스탬프가 반드시 필요합니다.

### 살릴 수 있는 자산

`CharacterStatus.currentStage`가 이미 있습니다. **9주차 "성장형 지능"의 레벨 값으로 그대로 쓸 수 있습니다.** AI 서버가 요청 시 이 값을 받아 프롬프트의 어휘 수준을 조정하면 됩니다.

다만 `closeness`와 `intimacy` 두 필드가 역할이 겹쳐 보입니다. 백엔드 확인이 필요합니다.

---

## 5. `userId` 타입

| 위치 | 타입 |
| --- | --- |
| `Conversation.userId` | `Long` |
| `CharacterStatus.userId` | `Integer` |

`Long`으로 통일을 제안합니다.

---

## 6. 음성 경로

현재 앱이 음성을 어떻게 서버로 보내는지 정의되어 있지 않습니다.

- 앱이 녹음 → 백엔드 업로드 → 백엔드가 AI 서버로 전달 (제안)
- 파일 포맷을 **명시적으로 합의**해야 합니다.

> ⚠️ 1학기에 Colab `MediaRecorder`가 webm으로 녹음한 파일을 `.wav` 이름으로 저장해, librosa가 폴백 경로로 읽었습니다. 감정 분석이 두 번 모두 `anger`로 나온 원인일 수 있습니다. **확장자가 아니라 실제 컨테이너 포맷을 합의하세요.** 권장: 16kHz mono WAV(PCM) 또는 표준 m4a.

---

## 확정 이력

| 날짜 | 항목 | 결정 |
| --- | --- | --- |
| 2026-09-21 | 초안 작성 | AI/PM |
|  | 1. AI 서버 호출 경로 | 협의 대기 |
|  | 2. 감정 라벨 분리 | 협의 대기 |
|  | 3. HW 제어값 | 협의 대기 |
|  | 4. MQTT JSON 전환 | 협의 대기 |
|  | 5. userId 타입 | 협의 대기 |
