# 인터페이스 정의서 v1.1 (2학기 1주차 · 10-01 개정)

> 작성: AI/PM · 2026-09-21 · **개정 2026-10-01**
> 대상: HW · 앱 · 백엔드 · AI 전 파트
> 근거: 2026-09-17 회의 결정(노션 「회의내용 정리 / 20260917」), 백엔드 `develop`(`e036b37`), HW `hw/Orbit/Orbit.ino`, `ai/app/schemas.py`

> **10-01 개정 사항.** v1(09-21)은 백엔드 코드(`0fad53a`)만 보고 "백엔드가 AI 서버를 호출하고 응답을 저장한다"는 구조를 제안했으나, 09-17 회의에서 이미 다른 구조로 정했습니다. 회의 결정과 그 뒤 백엔드·HW 구현을 기준으로 전 절을 고쳤습니다. v1에서 제안했다가 바뀐 내용은 각 절 끝의 "v1 대비"에 남겼습니다.

---

## 0. 요약

| # | 항목 | 결정 (09-17 회의) | 상태 |
| --- | --- | --- | --- |
| 1 | AI 서버 호출 경로 | 음성은 **키링 → AI 서버 직접**. AI 서버가 백엔드에서 맥락을 조회하고 대화 저장을 요청. 백엔드 → AI 호출은 산책(`/api/ai/walk`)만 | 확정. AI 서버 구현 필요 |
| 2 | 감정 값 | 공통 감정값 `happy` / `sad` / `angry` / `calm` | 확정. 백엔드 적용 완료. **AI 모델 출력 변환 규칙**은 2절 (이번 개정에서 제안) |
| 3 | HW 제어값 | OLED `EXPR_*`, 진동 이름 5종, LED 색 영어명. **HW가 실제로 구현한 값 기준** | 확정. AI 서버 enum 정리 필요 |
| 4 | MQTT | 토픽 `orbit/{deviceId}/status`, 사용자·캐릭터·키링 1:1:1 | 확정. 백엔드 구현 완료. 센서값 JSON 형식은 HW·백엔드 협의 중 |
| 5 | `userId` 타입 | — | 대화·미션은 `Long`, 미션 결과 요청 DTO는 `Integer`. 혼용 남아 있음 |

---

## 1. 호출 경로

### 결정 구조

```
[키링] 터치 → 녹음 ──POST /api/v1/interact/voice (wav + device_id + lux)──▶ [AI 서버]
                                                                          │
           STT · 감정 분석 · 미션 판정 · Gemini · TTS                     │
                                                                          │
[백엔드] ◀── Context API 조회 (device → 사용자, 단계, 오늘 미션, 최근 대화, 날씨) ──┤
[백엔드] ◀── 대화 저장 POST /api/conversations (requestId 포함, 백그라운드) ────────┤
[백엔드] ◀── 미션 결과 POST /api/missions/{missionId}/result (판정 시) ────────────┘
                                                                          │
[키링] ◀── 응답 (speech, audio_url, led, vibe, oled) ──────────────────────┘
[앱]   ── 대화 기록·캐릭터 상태는 백엔드에서 조회(GET)만

[앱] 텍스트 교신 ──▶ [AI 서버] (같은 흐름, channel = TEXT)
[백엔드] /api/ai/walk ──▶ [AI 서버] 산책 응답 생성 (백엔드가 산책 데이터를 준비해 호출)
```

| 원칙 | 내용 |
| --- | --- |
| Gemini 호출 | **AI 서버만.** 백엔드는 Gemini SDK와 키를 쓰지 않음 |
| 대화 저장 | **응답을 만든 곳이 저장 요청.** AI 서버가 백엔드 Conversation API를 호출. 앱은 대화를 POST하지 않음 |
| 저장 시점 | 사용자 응답을 먼저 내보내고 저장은 백그라운드. 백엔드가 실패해도 응답은 정상 |
| 중복 방지 | 요청마다 `requestId`. 재시도해도 같은 대화가 두 번 저장되지 않게 |
| 상태 변경 | 미션 완료·단계·연료·친밀도 변경은 **백엔드만** |

### 요청 스펙 — 키링 음성

```
POST /api/v1/interact/voice        (multipart/form-data)
  audio      : 16kHz mono WAV (PCM)   필수
  device_id  : string                 필수. 키링 MAC 기반 (예: ORBIT-001)
  lux        : int | null             조도
```

사용자·단계·날씨·최근 대화·오늘 미션은 **AI 서버가 `device_id`로 백엔드 Context API에서 조회**합니다. 키링은 이 정보를 모릅니다.

> 현재 `ai/app/api/v1/interact.py`는 `session_id`, `turn_no`, `lux`, `weather`, `mission_id`를 받고 `device_id`가 없습니다. 코드 수정 필요.

### 요청 스펙 — 앱 텍스트 (신규)

```
POST /api/v1/interact/text         (application/json)
  { "user_id": 1, "text": "오늘 좀 피곤해", "request_id": "..." }
```

09-17 회의에서 앱의 음성 교신 팝업을 텍스트 교신으로 전환하고 AI 서버를 거치기로 했습니다. 1단계 미션(기분 텍스트)이 이 경로로 들어옵니다. 미구현이며 위 필드는 제안입니다. 앱과 확정합니다.

### 요청 스펙 — 산책 (백엔드 → AI)

09-17 회의 안건 3. 백엔드 `WalkAiService`가 산책 데이터(거리·시간·위치·날씨·조도·현재 단계·사용자 발화)를 준비해 AI 서버를 호출합니다. 엔드포인트와 필드는 AI 서버 구현 시 확정합니다. 미구현.

### 응답 스펙

```json
{
  "speech": "치직- 대장님, 오늘 컨디션은 어떠십니까. 오버",
  "audio_url": "outputs/xxxx.wav",
  "led": "dim_blue",
  "vibe": "soft_continuous",
  "oled_expression": "EXPR_SAD",
  "user_text": "오늘 좀 힘들었어",
  "stt_confidence": 0.91,
  "user_emotion": "sad",
  "user_emotion_confidence": 0.87,
  "emotion": "sad",
  "latency": { "stt_ms": 0, "emotion_ms": 0, "llm_ms": 0, "tts_ms": 0, "total_ms": 0 },
  "llm_retry_count": 0,
  "fallback_triggered": false,
  "high_risk_detected": false
}
```

- `user_emotion` 은 AI 모델의 원래 라벨, `emotion` 은 2절 규칙으로 바꾼 공통값입니다. 앱·백엔드는 `emotion` 만 쓰면 됩니다.
- **HW 확인 필요:** 09-17 회의 추천 구조는 `hardware{led, vibe, oled}`로 묶는 형태였고, 현재 응답은 평평한 구조입니다. 결정 요약에 없는 항목이라 HW 파싱 방식에 맞춰 정합니다.
- **HW 확인 필요:** 응답 오디오는 현재 mp3입니다. 키링이 mp3를 디코딩할 수 없으면 wav(16kHz 모노)로 내려주기로 했으나 HW 확인 결과가 기록되어 있지 않습니다. 위 예시는 wav 기준입니다.

### v1 대비

v1은 "앱 → 백엔드 → AI 서버" 경로와 "백엔드가 AI 응답을 받아 저장"을 제안했습니다. 회의에서 키링이 마이크·스피커를 갖고(안건 2, 6) AI 서버로 직접 보내기로 했으므로 바뀌었습니다. 요청 필드의 `mission_id` / `mission_result` 는 AI 서버가 Context API로 오늘 미션을 조회하고 스스로 판정하므로 삭제했습니다(`docs/stage-mission-judgement.md`).

---

## 2. 감정 값

### 공통 감정값 (09-17 확정)

`happy` / `sad` / `angry` / `calm` — 백엔드 `Emotion` enum, 앱이 이 값을 씁니다. 대화 저장(`Conversation.emotion`)과 캐릭터 상태(오빗 기분)에 같은 값을 씁니다.

### AI 모델 출력 → 공통값 변환 (제안)

AI 감정 모델은 `sad` / `anger` / `fear` / `disgust` / `neutral` 5클래스를 출력합니다. 재학습 없이 공통값으로 바꾸는 규칙입니다. **AI 서버가 적용**해 응답 JSON의 `emotion` 필드로 내보내고, 대화 저장에도 이 값을 씁니다. 구현: `ai/app/core/emotion_map.py`, 테스트 `ai/tests/test_emotion_map.py`.

| 모델 출력 | 공통값 | 근거 |
| --- | --- | --- |
| `sad` | `sad` | 그대로 |
| `fear` | `sad` | 부정·저각성. 오빗 반응(부드럽고 따뜻한 톤)이 `sad`와 같음 |
| `anger` | `angry` | 그대로 |
| `disgust` | `angry` | 부정·고각성. 오빗 반응(예외 대화 3번)이 `anger`와 같음 |
| `neutral` | `calm` | 그대로 |
| `neutral` + 발화에 긍정 표현 | `happy` | **긍정 보정.** 모델에 긍정 클래스가 없어 텍스트로 보완. 아래 참조 |

- 원래 라벨(`user_emotion`)은 응답 JSON과 AI 서버 로그에 그대로 남깁니다. 고위험 발화 2차 탐지(sad/fear 연속 5턴)와 8주차 오분류 수집에 원래 라벨이 필요합니다.
- **긍정 보정 (10-01 채택).** 모델이 `neutral`이고 발화에 긍정 표현(좋·기쁘·행복·신나·설레·즐거·상쾌·뿌듯·재밌·최고)이 있으면 `happy`로 바꿉니다. 보정이 없으면 기쁜 발화가 전부 `calm`으로 저장되어 주간 감정 통계에서 긍정이 0으로 보입니다.
  - **부정·바람은 제외합니다.** "안 좋아", "좋지 않아", "못 즐겼어", "좋은 일이 없어", "별로 좋지 않아", "좋았으면 좋겠다"는 긍정이 아닙니다.
  - **`neutral`일 때만 보정합니다.** 모델이 `sad`·`anger` 등을 냈는데 텍스트에 "좋아"가 있다고 `happy`로 덮으면, 억양에서 잡은 부정 신호를 버리게 됩니다.
  - "괜찮아"·"편안해"는 `calm`에 가까워 긍정 표현에 넣지 않았습니다.
  - 키워드 방식의 한계(반어법, 사전에 없는 표현)는 6주차 회귀 테스트와 8주차 실사용 수집으로 보완합니다. 근본 해결은 긍정 클래스 재학습입니다.

### 오빗 기분 (캐릭터 상태)

v1에서 정리한 "사용자 감정과 오빗 기분은 다른 것"이라는 원칙은 유지합니다. 값만 공통값으로 바꿉니다. 변경은 **백엔드가** 합니다.

| 사건 | 오빗 기분 |
| --- | --- |
| 미션 성공 | `happy` |
| 사용자 감정 `sad` (모델 `sad` / `fear`) | `sad` |
| 사용자 감정 `angry` / `calm` | 변화 없음 (적대 발화에 오빗이 흔들리지 않음) |
| 기본값 | `calm` (`CharacterStatus` 기본값 `NORMAL` 교체, 백엔드 다음 계획에 포함됨) |

미션 성공 시 `happy`로 바꾸는 것이 **감정 모델 재학습 없이 오빗이 기뻐할 수 있는 경로**입니다.

---

## 3. 하드웨어 제어값

### 09-17 공통 제어값과 HW 구현 현황

| 구분 | 공통 제어값 (회의) | HW가 처리하는 값 (`applyHardwareAction`) |
| --- | --- | --- |
| OLED | `EXPR_NORMAL` / `HAPPY` / `SAD` / `SLEEP` / `BLINK` | `EXPR_NORMAL`, `EXPR_SAD`, `EXPR_LISTENING`, `EXPR_THINKING`, `EXPR_DIZZY` (+ 별칭 `idle_eyes`, `sad_eyes`). **`EXPR_HAPPY` 분기 없음** |
| 진동 | `soft_continuous`, `strong_double`, `calm_wave`, `short_pulse`, `two_short_taps` | `strong_double`, `short` / `short_pulse`, `soft_continuous`. **`calm_wave`, `two_short_taps` 미구현** |
| LED | 색깔 영어명 그대로 | `rainbow`, `dim_blue`, `purple`. 평상시에는 단계 테마색 |

HW가 처리하지 않는 값을 보내면 **아무 반응이 없습니다.** AI 서버는 오른쪽 열의 값만 씁니다.

### AI 서버가 보낼 값

| 상황 | `oled` | `led` | `vibe` |
| --- | --- | --- | --- |
| 긍정/중립 | `EXPR_NORMAL` | `rainbow` | `strong_double` |
| `sad` / `fear` / 조도 50 lux 이하 | `EXPR_SAD` | `dim_blue` | `soft_continuous` |
| `anger` / `disgust` | `EXPR_NORMAL` | `dim_blue` | `short_pulse` |
| 미션 성공 | `EXPR_HAPPY` | `rainbow` | `strong_double` |
| 미션 조건 미달 | `EXPR_NORMAL` | `dim_blue` | `short_pulse` |
| 미션 거부 (보류) | `EXPR_NORMAL` | `dim_blue` | `soft_continuous` |
| 처리 중 | `EXPR_THINKING` | — | — |
| 통신 장애 (비상 프로토콜) | `EXPR_SAD` | `dim_blue` | `short_pulse` |
| 고위험 발화 | `EXPR_SAD` | `dim_blue` | `none` (HW가 무시 → 진동 없음) |

- `anger` / `disgust` 는 v1에서 `dim_white` / `calm_wave` 였으나 HW에 없습니다. `calm_wave` 가 구현되면 진동을 되돌립니다.
- `anger` / `disgust` 와 미션 조건 미달의 LED는 처음에 "보내지 않음"으로 잡았으나 **`dim_blue` 로 정했습니다**(10-01). LED 값은 LLM이 고르거나 응답 필드에 반드시 들어가는 구조라 "없음"을 표현하려면 필드를 비울 수 있게 바꿔야 하는데, 그보다 단순한 쪽을 택했습니다. `sad` 와는 진동(`short_pulse`)으로 구분됩니다.
- 통신 장애는 v1에서 `orange` 였으나 HW에 없습니다. 비상 응답은 키링 플래시에 저장해 두고 로컬 재생하기로 했으므로(09-17 안건 2 장애 대응), 이 값은 서버가 살아 있고 Gemini만 실패한 경우에만 쓰입니다.

### 정할 것

- **LED의 의미.** HW는 평상시 LED를 단계 테마색(RTC 메모리 유지)으로 쓰고 있고, AI는 감정 색을 보냅니다. 회의에서 "단계 vs 감정, 둘 다라면 우선순위"를 정할 것으로 남겼습니다. 이 문서는 "평상시 단계색, AI 응답 시 잠시 감정색 후 단계색 복귀"를 제안합니다.
- **"색깔 영어명 그대로"와 `rainbow` / `dim_blue`.** 둘 다 순수 색 이름이 아닙니다. HW가 이미 이 이름으로 구현했으므로 유지하는 쪽을 제안합니다.

### v1 대비

v1은 AI enum(`idle_eyes`, `star_eyes`, `dim_white`, `calm_wave`, `orange`)을 기준으로 채택하자고 제안했습니다. 회의에서 HW 구현 기준으로 정했으므로 바뀌었습니다. AI 서버 코드(`ai/app/schemas.py` enum, `ai/prompts/persona.md` 매핑표, 비상·고위험·Vision 응답)도 10-01에 이 표 기준으로 바꿨습니다. `ai/tests/test_schemas.py` 가 프롬프트 매핑표의 값이 enum 안에 있는지 검사합니다.

---

## 4. MQTT

### 현재 구조 (백엔드 구현 완료)

| 항목 | 값 |
| --- | --- |
| 토픽 | `orbit/{deviceId}/status` (예: `orbit/ORBIT-001/status`) |
| 식별 | 백엔드가 토픽에서 `deviceId`를 꺼내 Device DB로 `charId`/`userId` 조회 |
| 관계 | 사용자 · 캐릭터 · 키링 1:1:1 |
| payload | 문자열 `FUEL_UP`, `LOVE_UP`, `JACKPOT_SUCCESS`, `happy`/`sad`/`angry`/`calm`, `TOUCHED` |
| 단계 상승 | `STAGE_UP` **제거됨.** 미션 성공 시 백엔드만 올림 |

### 미션 판정과의 관계

v1은 MQTT 센서값으로 미션을 판정하는 것을 전제로 JSON 전환을 요구했으나, 09-17 회의에서 미션 4종(기분 텍스트·날씨 음성·랜드마크 사진·대중교통)을 AI 판정으로 정했으므로 **MQTT는 미션 판정 경로가 아닙니다.** 센서값 JSON 전환은 스탯·탐사 기록(걸음 수 등)용으로 HW·백엔드가 정합니다. 전환한다면 HW가 찍은 `ts`(밀리초)를 넣을 것을 권합니다.

---

## 5. `userId` 타입

| 위치 | 타입 |
| --- | --- |
| `Conversation.userId`, `UserMission.userId` | `Long` |
| `MissionResultRequest.userId`, `MissionController`의 `@RequestParam` | `Integer` |

`Long`으로 통일을 제안합니다(v1과 같음).

---

## 6. 음성 형식

- **키링 → AI 서버:** 16kHz mono WAV(PCM). WROOM-32의 RAM이 약 300KB라 녹음을 통째로 모으지 말고 나눠 전송합니다(09-17 회의).
- **AI 서버 → 키링:** 1절 응답 스펙 참조. mp3/wav 미정.

> 1학기에 Colab `MediaRecorder`가 webm으로 녹음한 파일을 `.wav` 이름으로 저장해 librosa가 폴백 경로로 읽었습니다. **확장자가 아니라 실제 컨테이너 포맷을 맞추세요.**

---

## 확정 이력

| 날짜 | 항목 | 결정 |
| --- | --- | --- |
| 2026-09-17 | 호출 경로 | 키링 → AI 서버 직접, AI가 맥락 조회·대화 저장. Gemini는 AI 서버만 (회의 안건 2·3·5) |
| 2026-09-17 | 감정 값 | `happy` / `sad` / `angry` / `calm` (안건 1) |
| 2026-09-17 | HW 제어값 | HW 구현 기준. OLED `EXPR_*` (안건 1) |
| 2026-09-17 | 식별 구조 | 사용자·캐릭터·키링 1:1:1, MQTT 토픽에 `deviceId` (안건 5) |
| 2026-09-21 | v1 초안 | AI/PM |
| 2026-10-01 | v1.1 개정 | 09-17 결정 반영. AI 모델 출력 → 공통 감정값 변환 규칙 제안 |
| 2026-10-01 | 감정 긍정 보정 | `neutral` + 긍정 표현 → `happy` 채택 (AI/PM). AI 서버 구현 완료 |
|  | 감정 변환 규칙 (라벨 매핑 + 긍정 보정) | 팀 승인 대기. AI 서버는 이 규칙으로 구현됨 |
|  | LED 의미 (단계 vs 감정) | 협의 대기 |
|  | 응답 JSON 구조 · 응답 오디오 형식 | HW 확인 대기 |
|  | `userId` 타입 | 협의 대기 |
