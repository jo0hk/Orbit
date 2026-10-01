# 대화 로그 스키마 정의서 (2학기 2주차 · 10-01 개정)

> 작성: AI/PM · 2026-09-21 · **개정 2026-10-01**
> 대상: 백엔드 · AI
> 기준: 2026-09-17 회의 안건 5, 백엔드 `develop`(`e036b37`)의 `Conversation` / `ConversationRequest`

> **10-01 개정 사항.** 초판(09-21)은 "백엔드가 AI 서버 응답을 그대로 받아 저장하고, 필드 21개를 추가한다"는 전제였습니다. 09-17 회의에서 **AI 서버가 저장을 요청**하고 **추가 컬럼은 `emotion` / `stage` / `channel` / `requestId` 4개**로 정했고, 백엔드가 5주차에 이를 구현했습니다. 이에 맞춰 고쳤습니다. 초판의 나머지 필드는 4절에 "추가 제안"으로 남겼습니다.

---

## 1. 저장 주체와 흐름 (09-17 확정)

```
키링(음성) ─┐
            ├─▶ AI 서버 ── 응답 생성 ──▶ 사용자에게 응답
앱(텍스트) ─┘        │
                    └──(백그라운드)──▶ 백엔드 POST /api/conversations  × 2 (USER, ORBIT)
                                                   ▲
                                         앱은 조회(GET)만
```

| 규칙 | 내용 |
| --- | --- |
| 저장 주체 | **응답을 만든 AI 서버만.** 앱은 대화를 POST하지 않음 (앱의 `ConversationRequestDto`는 쓰지 않음) |
| 시점 | 사용자 응답을 먼저 내보내고 저장은 FastAPI `BackgroundTasks` |
| 실패 | 백엔드 저장 실패 시에도 사용자 응답은 정상. 로그만 남김 |
| 중복 방지 | 요청마다 `requestId`. 재시도해도 두 번 저장되지 않게 |
| 암호화 | 메시지 본문은 AES-GCM 암호화(백엔드 `CryptoService`). 감정 라벨은 평문 — 날짜별 통계에 필요하고 라벨만으로는 대화 내용을 알 수 없음 |

---

## 2. 현재 스키마 (백엔드 구현 완료)

```java
public class ConversationRequest {
    private Long userId;
    private Speaker speaker;               // USER | ORBIT
    private String message;                // 암호화 저장
    private String emotion;                // 공통 감정값 (Emotion enum 검증)
    private Integer stage;                 // 대화 당시 단계 1~4
    private ConversationChannel channel;   // TEXT | VOICE
    private String requestId;              // 중복 방지
}
```

| API | 용도 |
| --- | --- |
| `POST /api/conversations` | 저장 (AI 서버가 호출) |
| `GET /api/conversations/{userId}` | 전체 조회 (앱 타임라인) |
| `GET /api/conversations/{userId}/recent?limit=10` | 최근 N개 (AI 프롬프트용, 기본 10 = 5턴) |

---

## 3. AI 서버가 채우는 값

한 턴은 USER 행과 ORBIT 행 **2개**로 저장합니다.

| 필드 | USER 행 | ORBIT 행 |
| --- | --- | --- |
| `userId` | Context API로 `device_id` → `userId` 변환 (음성) / 요청값 (텍스트) | 동일 |
| `speaker` | `USER` | `ORBIT` |
| `message` | STT 결과 또는 입력 텍스트 | `speech` |
| `emotion` | AI 모델 출력을 공통값으로 변환 (`interface-spec-v1.md` 2절: sad·fear→`sad`, anger·disgust→`angry`, neutral→`calm`) | 비움 |
| `stage` | Context API의 현재 단계 | 동일 |
| `channel` | `VOICE` (키링) / `TEXT` (앱) | 동일 |
| `requestId` | 요청 하나에 하나 발급. 두 행이 같은 값을 쓰면 백엔드가 중복으로 볼 수 있으므로 `{requestId}-U` / `{requestId}-O` 처럼 구분 | 〃 |

> **고위험 발화 턴도 저장합니다.** 고정 응답을 ORBIT 행으로 남깁니다. 정책 문서(`docs/high-risk-utterance-policy.md`)의 2차 탐지(sad/fear 연속 5턴)와 사후 확인에 필요합니다. 다만 공통값으로 바꾸면 `fear`가 `sad`로 합쳐지므로, 2차 탐지는 AI 서버가 원래 라벨로 직접 셉니다(4절 참고).

> **`requestId` 두 행 처리는 백엔드 확인이 필요합니다.** 백엔드가 `requestId`를 고유 키로 쓴다면 위처럼 접미사로 구분해야 합니다.

---

## 4. 추가 제안 (미합의)

초판에서 제안했던 필드 중 회의에서 채택되지 않은 것입니다. 필요성이 생기면 다시 협의합니다.

| 필드 | 용도 | 필요해지는 시점 |
| --- | --- | --- |
| `rawEmotion` | AI 모델 원래 라벨 (5클래스) | 고위험 2차 탐지를 백엔드 이력으로 하려면. 8주차 오분류 수집 |
| `sttConfidence` | 음성 인식 신뢰도 | 8주차 야외 STT 검증 |
| `latencyTotalMs` 및 단계별 | 응답 시간 | 레이턴시 추적. 지금은 AI 서버 로그로 대신함 |
| `fallbackTriggered`, `highRiskDetected` | 비상·안전 대응 발동 | 운영 통계 |
| `led`, `vibe`, `oledExpression` | HW 신호 | 6주차 회귀 테스트에서 신호 검증 |

미션 판정 기록은 대화 테이블이 아니라 백엔드 `user_missions`(상태·완료 시각)에 남습니다. 판정 사유 코드(`reason`)를 남기려면 미션 결과 API에 필드를 추가합니다(`docs/stage-mission-judgement.md` 3절).

---

## 5. AI가 활용할 정보

| 활용 정보 | 산출 방법 | 쓰이는 곳 |
| --- | --- | --- |
| 최근 대화 | `recent?limit=10` (Context API에 포함) | 문맥 유지 |
| 주간 부정 감정 비율 | `emotion` 집계 (`sad`, `angry`) | 톤 조절. 다만 사용자 발화에 `happy`가 붙지 않으므로 긍정 비율은 알 수 없음 |
| 누적 교신 수 | `COUNT(*)` | 9주차 성장 레벨 |
| 완료 미션 수 | `user_missions` `COMPLETED` 집계 | 9주차 성장 레벨 |
| 최근 사용 문형 | 최근 ORBIT 발화 | 9주차 반복 칭찬 방지 |

---

## 6. 남은 확인 사항

| 항목 | 담당 |
| --- | --- |
| `requestId` 고유 키 여부와 USER/ORBIT 두 행 처리 | 백엔드 |
| `userId` 타입 통일 (`Long`) | 백엔드 |
| `emotion` 변환 규칙 승인 | 전체 (`interface-spec-v1.md` 2절) |
| 전체 조회 API 페이지 나누기 (대화가 쌓이면 매번 전체 복호화) | 백엔드 |
