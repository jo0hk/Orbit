# 대화 로그 스키마 정의서 (2학기 2주차)

> 작성: AI/PM · 2026-09-21
> 대상: 백엔드
> 기준: `backend/.../entity/Conversation.java` (커밋 `0fad53a`)

---

## 1. 현재 구현 상태

백엔드에 대화 저장이 **이미 구현되어 있습니다.**

```java
@Entity @Table(name = "conversations")
public class Conversation {
    private Long id;
    private Long userId;
    private Speaker speaker;       // USER | ORBIT
    private String message;        // AES/GCM 암호화 저장
    private LocalDateTime createdAt;
}
```

- `POST /api/conversations` 저장, `GET /api/conversations/{userId}` 조회
- `CryptoService`가 AES/GCM으로 암·복호화. 조회 시 자동 복호화됨

**따라서 2주차 과제는 "정의"가 아니라 "확장"입니다.**

> ✅ 3주차 우려 해소: 암호화 때문에 AI가 과거 대화를 못 읽을까 걱정했으나, `ConversationService.toResponse()`가 조회 시 복호화하므로 AI 서버가 그대로 활용할 수 있습니다.

---

## 2. 추가가 필요한 필드

AI가 응답을 만들고 나면 감정·환경·하드웨어 신호가 함께 나옵니다. 지금은 `message` 하나만 저장돼서 **전부 버려지고 있습니다.**

| 필드 | 타입 | 용도 | 주차 |
| --- | --- | --- | --- |
| `sessionId` | `String` | 한 번의 교신 묶음 | 2 |
| `turnNo` | `Integer` | 세션 내 순번 | 2 |
| `userEmotion` | `String` | AI 감정 분석 결과 (5클래스) | 2 |
| `userEmotionConfidence` | `Double` | 감정 신뢰도 | 2 |
| `sttConfidence` | `Double` | 음성 인식 신뢰도 | 2 |
| `lux` | `Integer` | 조도 | 2 |
| `weather` | `String` | 날씨 | 2 |
| `locationCoarse` | `String` | 비식별 위치 | 2 |
| `led` | `String` | HW 신호 | 2 |
| `vibe` | `String` | HW 신호 | 2 |
| `oledExpression` | `String` | HW 신호 | 2 |
| `latencyTotalMs` | `Integer` | 전체 응답 시간 | 2 |
| `latencySttMs` | `Integer` | 단계별 | 2 |
| `latencyEmotionMs` | `Integer` | 단계별 | 2 |
| `latencyLlmMs` | `Integer` | 단계별 | 2 |
| `latencyTtsMs` | `Integer` | 단계별 | 2 |
| `llmRetryCount` | `Integer` | 재시도 횟수 | 2 |
| `fallbackTriggered` | `Boolean` | 비상 프로토콜 발동 여부 | 2 |
| `highRiskDetected` | `Boolean` | 고위험 발화 대응 발동 여부 | 3 |
| `missionId` | `String` | 관련 미션 | 4 |
| `missionResult` | `String` | success/fail/retry | 5 |
| `distanceM` | `Integer` | GPS 누적 거리 | 7 |

### 암호화 대상

| 대상 | 암호화 |
| --- | --- |
| `message` | ✅ (현행 유지) |
| `locationCoarse` | ✅ 권장 |
| 나머지 메타데이터 | ❌ 불필요 |

감정·레이턴시·HW 신호는 개인 식별 정보가 아니고, 암호화하면 통계 집계가 불가능해집니다.

### 레이턴시 필드가 중요한 이유

1학기 일지의 "6초대"는 **유효한 측정값이 아닙니다.** 벤치마크 실행 당시 API 키가 비어 있어 Gemini 호출이 전부 실패했고, tenacity 백오프 대기 시간이 그대로 기록됐습니다.

기준선이 없는 상태이므로, **매 턴 자동으로 쌓이는 로그**가 유일한 관측 수단입니다. 미션 판정이 붙는 5주차 이후 어느 단계에서 느려졌는지 이 필드 없이는 찾을 수 없습니다.

---

## 3. AI가 활용할 정보

저장만 하고 안 쓰면 의미가 없습니다. AI 서버가 실제로 읽어갈 항목입니다.

| 활용 정보 | 산출 방법 | 쓰이는 곳 |
| --- | --- | --- |
| 최근 N턴 요약 | 최근 대화 조회 후 요약 | 문맥 유지 |
| 주간 부정 감정 비율 | `userEmotion` 집계 | 톤 조절 |
| 선호 주제 키워드 | `message` 빈도 분석 | 대화 소재 |
| 누적 교신 수 | `COUNT(*)` | 9주차 성장 레벨 |
| 누적 탐사 거리 | `SUM(distanceM)` | 9주차 성장 레벨 |
| 완료 미션 수 | `missionResult='success'` 집계 | 9주차 성장 레벨 |
| 최근 사용 문형 | 최근 `ORBIT` 발화 | 9주차 반복 칭찬 방지 |

### ⚠️ 조회 API에 개수 제한이 필요합니다

```java
public List<ConversationResponse> getConversations(Long userId) {
    return conversationRepository.findByUserIdOrderByCreatedAtAsc(userId)  // 전체 반환
```

대화가 쌓이면 이 API가 전체를 복호화해서 반환합니다. AI가 프롬프트에 넣을 수도 없고 응답도 느려집니다.

**제안**

```
GET /api/conversations/{userId}?limit=20&order=desc
```

`CryptoService.decrypt()`가 행마다 호출되므로, 개수 제한은 성능에도 직접 영향을 줍니다.

---

## 4. `Speaker` enum

```java
public enum Speaker { USER, ORBIT }
```

현행 유지로 충분합니다. 다만 한 턴이 USER 행 + ORBIT 행 **2개**로 저장되는데, 감정·레이턴시·HW 신호는 ORBIT 행에만 의미가 있습니다.

**권장**: `sessionId` + `turnNo`로 두 행을 묶고, 메타데이터는 `ORBIT` 행에 기록합니다. `USER` 행에는 `sttConfidence`와 `userEmotion`만 둡니다.

---

## 5. 백엔드 작업 요약

1. `Conversation` 엔티티에 위 필드 추가 (마이그레이션)
2. `ConversationRequest` DTO 확장 — AI 서버 응답을 그대로 받도록
3. `GET /api/conversations/{userId}`에 `limit` 파라미터 추가
4. `userId` 타입을 `Long`으로 통일 (`CharacterStatus`는 현재 `Integer`)
5. 집계용 조회 메서드 (누적 교신 수 / 거리 / 미션) — 9주차 전까지

AI 서버 응답 JSON은 `docs/interface-spec-v1.md` 1절을 참조하세요. 필드명이 그대로 대응됩니다.
