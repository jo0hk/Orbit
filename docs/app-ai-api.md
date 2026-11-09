# 앱 ↔ AI 서버 API (텍스트 교신 확정 · 사진 판정 제안)

> 작성: AI/PM · 2026-11-09
> 대상: 앱
> 근거: `docs/interface-spec-v1.md` 1절(11-09 개정), `docs/stage-mission-judgement.md`, `docs/mission-context-injection.md`, 앱 `feature/app` 브랜치 `AiApi.kt`·`MainActivity.kt`(`b8e9ce9`)

앱이 AI 서버에 직접 붙는 API를 정리한 문서입니다. **텍스트 교신은 구현과 백엔드 연동 확인까지 끝났습니다.** 사진 판정은 형식을 먼저 앱과 정한 뒤 구현합니다.

---

## 0. 요약

| API | 용도 | 상태 |
| --- | --- | --- |
| `POST /api/v1/interact/text` | 앱 텍스트 교신. 1단계 미션(기분 텍스트)이 여기로 들어옴 | **구현 완료.** 11-09 로컬 백엔드와 연동 확인 |
| `POST /api/v1/interact/photo` | 3단계 랜드마크 사진, 4단계 대중교통 승차·하차 사진 | **제안.** 3절 형식을 정하면 구현 |
| `POST /api/v1/interact/voice` | 키링 음성. 앱은 쓰지 않음 | 구현 완료 (키링 쪽 녹음·전송은 HW 작업) |
| `GET /health` | 서버 살아 있는지 확인 | 구현 완료 |

앱은 대화 기록·캐릭터 상태·오늘 미션을 지금처럼 **백엔드에서 조회(GET)** 합니다. 미션 완료·단계 상승·대화 저장은 AI 서버가 백엔드에 요청하므로 앱이 따로 할 일이 없습니다.

---

## 1. 공통

| 항목 | 내용 |
| --- | --- |
| 주소 | 연동 테스트 때 AI/PM이 터널 주소를 전달합니다. Retrofit `BASE_URL`은 끝에 `/`를 붙여 주세요 |
| 응답 시간 | 11-09 측정 텍스트 약 3~7초(대부분 Gemini). `readTimeout` 30초 유지를 권장합니다 |
| 백엔드 장애 | AI 서버가 백엔드에 못 붙어도 응답은 정상으로 나갑니다. 이때는 미션 판정과 대화 저장이 되지 않습니다 |
| Gemini 장애 | 비상 응답이 나갑니다(`fallback_triggered: true`). 에러가 아니라 정상 응답이므로 `speech`를 그대로 보여 주면 됩니다 |
| 입력 오류 | `422` + FastAPI 기본 형식(`{"detail": [...]}`) |
| 서버 오류 | `500`. 앱은 기존처럼 "전송 실패" 안내 |

---

## 2. 텍스트 교신 — 확정

### 요청

```
POST /api/v1/interact/text
Content-Type: application/json

{
  "user_id": 1,
  "text": "오늘 좀 피곤해",
  "request_id": "b2f0c6e4-..."
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `user_id` | Long | 필수 | 백엔드 사용자 ID |
| `text` | String | 필수 | 1~500자 |
| `request_id` | String | 선택 | 메시지마다 앱이 UUID를 만들어 넣고, **같은 메시지를 재전송할 때는 같은 값**을 씁니다. 없으면 서버가 발급 |

### 응답

```json
{
  "speech": "치직- 본부에 긴급 타전! 대장님 첫 상태 보고 수신 완료. 라저",
  "led": "rainbow",
  "vibe": "strong_double",
  "oled_expression": "EXPR_HAPPY",
  "audio_url": null,
  "user_text": "오늘 좀 피곤해",
  "stt_confidence": null,
  "user_emotion": "neutral",
  "user_emotion_confidence": null,
  "emotion": "calm",
  "latency": { "stt_ms": 0, "context_ms": 193, "emotion_ms": 0, "llm_ms": 6290, "tts_ms": 0, "total_ms": 6484 },
  "llm_retry_count": 0,
  "fallback_triggered": false,
  "high_risk_detected": false,
  "mission_result": "success",
  "request_id": "b2f0c6e4-..."
}
```

앱이 쓰면 되는 필드는 4개입니다. 나머지는 키링·로그용이라 무시해도 됩니다.

| 필드 | 값 | 앱에서 할 일 |
| --- | --- | --- |
| `speech` | 오빗 대사 | 말풍선에 표시. **고위험 대응 문구는 여러 줄이고 45자를 넘습니다.** 줄바꿈이 보이게 해 주세요 |
| `mission_result` | `success` / `retry` / `deferred` / `none` | `success`면 미션 성공 화면. 나머지는 대사만 보여 주면 됨 (`retry`는 같은 날 다시 할 수 있음, `deferred`는 사용자가 거부해서 보류) |
| `high_risk_detected` | Boolean | `true`면 위기 안내 팝업 |
| `emotion` | `happy` / `sad` / `angry` / `calm` | 캐릭터 얼굴 등에 쓸 수 있음 (공통 감정값) |

- **"실패"는 없습니다.** `retry`를 "실패"로 표시하지 말아 주세요(09-17 회의 결정).
- 미션 판정은 오늘 미션이 1단계(기분 텍스트)이고 아직 진행 중일 때만 합니다. 2단계는 키링 음성 미션이라 앱 텍스트로 날씨를 말해도 판정하지 않습니다.
- 미션 완료·단계 상승은 응답을 보낸 **직후** 백그라운드에서 백엔드에 반영됩니다. 성공 화면 뒤에 단계를 다시 불러올 때는 1초쯤 뒤에 `GET /api/missions/current`, `GET /api/character/{id}`를 호출하면 됩니다.
- 텍스트 교신의 `emotion`은 지금 긍정 표현이 있으면 `happy`, 아니면 `calm`입니다. 감정 모델이 음성과 함께 학습되어 텍스트만으로는 돌리지 않기 때문입니다(개선 예정).

### `AiApi.kt` 변경 예시

현재 앱 코드와의 대응입니다. 앱이 Gson을 쓰므로 `@SerializedName`으로 이름만 맞추면 됩니다.

| 현재 앱 코드 | 바꿀 값 |
| --- | --- |
| `@POST("ai/chat")` | `@POST("api/v1/interact/text")` |
| `ChatRequest(userId, message)` | `user_id`, `text`, `request_id` |
| `AiResponse.reply` | `speech` |
| `AiResponse.missionSuccess` | `mission_result == "success"` |
| `AiResponse.crisisDetected` | `high_risk_detected` |

```kotlin
data class ChatRequest(
    @SerializedName("user_id") val userId: Long,
    @SerializedName("text") val text: String,
    @SerializedName("request_id") val requestId: String = java.util.UUID.randomUUID().toString()
)

data class AiResponse(
    @SerializedName("speech") val speech: String? = null,
    @SerializedName("mission_result") val missionResult: String? = null,  // success / retry / deferred / none
    @SerializedName("high_risk_detected") val highRiskDetected: Boolean? = null,
    @SerializedName("emotion") val emotion: String? = null
) {
    val missionSuccess: Boolean get() = missionResult == "success"
}

interface AiApiService {
    @POST("api/v1/interact/text")
    suspend fun sendChat(@Body request: ChatRequest): AiResponse
}
```

### 앱 쪽 확인 요청

| # | 내용 | 이유 |
| --- | --- | --- |
| 1 | 앱의 대화 저장 호출(`ConversationApi.saveConversation`, `POST /api/conversations`)을 빼 주세요. 대화 목록 조회(GET)는 그대로 | 09-17 회의에서 대화 저장은 AI 서버만 요청하기로 함. 앱도 저장하면 같은 대화가 두 번 쌓임 |
| 2 | `userId = 1L` 하드코딩은 연동 테스트 동안은 그대로 써도 됩니다 | 테스트 사용자도 1번 |

---

## 3. 사진 판정 — 제안 (미구현)

3단계(랜드마크)와 4단계(대중교통)를 사진으로 판정합니다. 판정 조건은 `docs/stage-mission-judgement.md` 3·4단계, 반응 대사는 `ai/prompts/missions.md`에 있습니다. **아래 형식에 앱이 동의하면 구현을 시작합니다.**

### 미션별 판정 조건 (요약)

| 단계 | 인증 | 성공 조건 |
| --- | --- | --- |
| 3 랜드마크 | 사진 1장 | 야외 사진, 피사체가 건물·조형물·간판, Vision 신뢰도 0.6 이상. 사람이 주 피사체면 다시 찍기 안내 |
| 4 대중교통 | **승차·하차 사진 2장** | 승차: 교통카드 단말기·하차벨·노선도 중 하나. 하차: 정류장 표지판·역명판. 두 촬영의 **시간차 5분 이상**, **직선거리 1km 이상** |

4단계는 09-17 회의 피드백("GPS로 미세한 위치 판정이 어렵다")에 따라 GPS 이동 거리 대신 카메라 인증으로 정했습니다.

### 요청 (제안)

```
POST /api/v1/interact/photo
Content-Type: multipart/form-data

  image        : JPEG               필수. 카메라 촬영만 (갤러리 선택 불가)
  user_id      : Long               필수
  captured_at  : String             필수. 촬영 시각, ISO 8601 + 시간대 (예: 2026-11-10T14:03:22+09:00)
  step         : String             4단계만 필수. boarding(승차) | alighting(하차)
  lat, lng     : Double             4단계만 필수. 촬영 시점 위치
  request_id   : String             선택. 텍스트와 같은 규칙
```

- **`missionId`는 보내지 않아도 됩니다.** AI 서버가 백엔드에서 오늘 미션을 조회해 3단계인지 4단계인지 판단합니다.
- **3단계는 위치를 보내지 않습니다.** 판정에 필요 없는 위치는 받지 않습니다.
- 4단계 위치는 두 지점 사이 거리 계산에만 쓰고 저장하지 않습니다. 사진 원본도 판정 후 저장하지 않습니다.
- 이미지는 긴 변 1280px 안팎, 2MB 이하를 권장합니다.

### 응답 (제안)

텍스트와 같은 형식에 필드 1개를 더합니다.

| 필드 | 값 | 설명 |
| --- | --- | --- |
| `mission_result` | `success` / `retry` / `none` | 3단계는 판정 결과. 4단계 승차 사진이 인정되면 아직 미션이 끝나지 않았으므로 `none` |
| `next_step` | `alighting` / `null` | 4단계 승차 인증이 끝났으니 하차 사진을 찍으라는 뜻. 앱은 하차 촬영 버튼을 보여 주면 됨 |
| `speech` | 오빗 대사 | 예: 승차 인정 시 "탑승 확인, 하차 후 송신 바람" 류의 안내 |

### 앱 코드에서 바뀌어야 할 것

| 현재 앱 코드 | 문제 | 제안 |
| --- | --- | --- |
| `ActivityResultContracts.TakePicturePreview()` | 썸네일 크기 비트맵만 받음. 간판·역명판이 작게 찍혀 Vision 판정이 어려울 수 있음 | `TakePicture()`로 원본을 파일에 받은 뒤 1280px로 줄여 전송 |
| `sendPhoto(image, userId, missionId)` | 촬영 시각·위치·단계 없음 | 위 요청 형식 |
| `sendGps` (100m마다 이동 거리 전송) + 상시 위치 추적 | 4단계를 사진 인증으로 바꿔서 쓰지 않음. 상시 위치 추적은 개인정보 원칙(필요한 만큼만)과도 맞지 않음 | 제거. 위치는 4단계 촬영 순간에만 읽기 |

### 정할 것

| # | 항목 | 추천 | 이유 |
| --- | --- | --- | --- |
| 1 | 4단계 승차 기록을 어디에 둘지 | AI 서버 메모리에 당일만 보관 | 백엔드 테이블을 새로 만들 필요가 없음. 서버를 재시작하면 승차부터 다시 찍어야 하는 단점은 시연 범위에서 감수 가능 |
| 2 | 하루 판정 횟수를 넘겼을 때 | `200` + 안내 대사, `mission_result: none` | 3단계 5회, 4단계 승차·하차 각 3회 (Gemini 무료 한도). 에러 화면보다 오빗 대사로 안내하는 편이 자연스러움 |
| 3 | 갤러리 차단 | 앱에서만 막음 | 서버는 사진이 카메라로 찍혔는지 확실히 알 수 없음(EXIF가 없을 수 있음) |
| 4 | 4단계 하차 사진을 다음 날 보내는 경우 | 승차 기록 만료, 승차부터 다시 | 미션이 하루 단위로 배정됨 |
