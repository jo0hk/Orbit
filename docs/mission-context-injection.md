# 미션 결과 주입 프롬프트 템플릿 (2학기 5주차)

> 작성: AI/PM · 2026-09-28
> 대상: AI 서버 · 백엔드
> 선행 문서: `docs/mission-spec.md` (판정 조건) · `ai/prompts/missions.md` (대사 세트) · `ai/prompts/persona.md`
> 적용 위치: `ai/app/core/context.py` `build_system_prompt()` 의 `TODO(5주차)` 자리

이 문서는 두 가지를 정합니다.

1. 미션 결과(`success` / `fail` / `retry`)를 감정·조도·날씨와 함께 **Context Injector에 주입하는 템플릿**
2. "우주 수준의 화려한 피드백"을 **45자 규칙 안에서** 살리는 성공 반응 문형

---

## 0. 먼저 해결해야 할 것 — 현재 코드로는 미션 결과가 주입되지 않습니다

| # | 위치 | 문제 | 조치 |
| --- | --- | --- | --- |
| 1 | `ai/app/api/v1/interact.py` | `mission_result` 를 `Form`으로 받지 않습니다. `EnvContext` 기본값 `NONE`이 들어가므로 **어떤 값을 보내도 미션 블록이 생성되지 않습니다.** 인터페이스 정의서 v1에 있는 `distance_m` / `location` 도 같은 상태입니다 | `mission_result: MissionResult = Form(MissionResult.NONE)` 추가 후 `EnvContext`에 전달 |
| 2 | `ai/app/core/pipeline.py` | LLM 응답 뒤 `oled_for(emotion)` 로 표정을 덮어씁니다. 미션 성공 턴에도 사용자 감정(예: `sad`)에 따라 `sad_eyes` 가 나갑니다 | 미션 결과가 있으면 `missions.py` 의 `SIGNAL_*` 로 덮어쓰기 (3절) |
| 3 | 용어 | 인터페이스는 `success / fail / retry`, 미션 상태는 `SUCCESS / TIMEOUT / DEFERRED` 이고 **`FAILED`는 없습니다** (4주차 결정) | 1절 매핑표로 고정. 프롬프트에 "실패"라는 단어를 넣지 않음 |

1번이 없으면 이 문서의 템플릿은 호출되지 않습니다. 코드 변경은 한 줄 수준입니다.

---

## 1. 결과값 매핑

인터페이스 값(`MissionResult`)은 바꾸지 않고, **의미를 미션 상태에 고정**합니다.

| `mission_result` | 미션 상태 | 의미 | 사용할 대사 | HW 신호 |
| --- | --- | --- | --- | --- |
| `success` | `SUCCESS` | 조건 충족 | `Mission.success` | `SIGNAL_SUCCESS` — `rainbow` · `strong_double` · `star_eyes` |
| `retry` | `TIMEOUT` | 시간 안에 조건 미달. 다시 할 수 있음 | `Mission.retry` | `SIGNAL_TIMEOUT` — `dim_blue` · `short` · `idle_eyes` |
| `fail` | `DEFERRED` | 사용자가 거부했거나 중단. **다시 권하지 않음** | 예외 대화 1번 톤 | `SIGNAL_DEFERRED` — `dim_blue` · `soft_continuous` · `idle_eyes` |
| `none` | — | 미션과 무관한 턴 | — | 감정 매핑 (기존) |

> `fail` 이라는 이름은 4주차 "실패 판정을 두지 않는다" 원칙과 어긋납니다. 이름을 `deferred` 로 바꾸는 것이 맞지만 백엔드와 합의된 인터페이스 값이라 이번 주에는 **의미만 고정**합니다. 6주차 인터페이스 v2에서 이름 변경을 제안합니다.

---

## 2. 언제 주입하는가 — 전달 경로

미션 판정은 MQTT 이벤트로 백엔드에서 일어나고, AI 서버는 **사용자 음성이 들어올 때만** 호출됩니다. 판정 순간과 오빗이 말하는 순간이 다릅니다.

### 채택안: HW 신호는 즉시, 대사는 다음 음성 턴

```
[HW] TOUCH/LUX 이벤트 ─▶ [백엔드] 판정 SUCCESS
                            ├─▶ MQTT: led/vibe/oled 즉시 송신 (말 없이 반짝임)
                            └─▶ 대기열에 (mission_instance_id, success) 저장

[앱] 사용자 발화 ─▶ [백엔드] 대기열에서 꺼냄 ─▶ [AI 서버] mission_id + mission_result=success
                                                   └─▶ 축하 대사 생성
```

- **현재 API를 그대로 씁니다.** 새 엔드포인트가 필요 없습니다.
- 사용자는 불빛·진동으로 즉시 반응을 받고, 보통 "됐어?" / "했어!" 라고 말합니다. 그 턴에서 오빗이 축하합니다.

### 주입 규칙 (백엔드)

| 규칙 | 값 | 이유 |
| --- | --- | --- |
| 1회 소비 | `mission_instance_id` 당 **정확히 1턴**만 `mission_result` 를 실어 보냄 | 칭찬 중복 방지 (6주차 검증 항목) |
| 유효 시간 | 판정 후 **10분** 안에 음성 턴이 없으면 폐기 | 한참 뒤 뜬금없는 축하 방지. HW 신호로 이미 반응함 |
| 동시 발생 | 대기 중인 결과가 둘 이상이면 **가장 최근 1건**만 | 45자 안에 두 미션을 다룰 수 없음 |
| 이월 | AI 응답의 `mission_ack=false` 면 다음 턴에 한 번 더 실음 (최대 1회) | 4절 끼어들기 규칙 |

### 대안 (보류): 판정 즉시 고정 대사

판정 순간 `missions.py` 의 대사를 TTS로 바로 재생하는 방식입니다. 반응은 빠르지만 텍스트 없는 호출용 엔드포인트가 새로 필요하고 LLM을 거치지 않아 다양성이 없습니다. 10주차 시연 안정성이 부족하면 그때 검토합니다.

---

## 3. 프롬프트 템플릿

### 3-1. 삽입 위치와 순서

```
persona.md
[현재 대장님의 우주 기지(환경) 정보]   ← 기존: 감정 · 위치 · 날씨 · 조도
  + - 미션 교신: {mission_name} → {result_label}          ← 추가 (한 줄)
[환경별 컨텍스트 제어 수칙]            ← 기존. 단, 3-3의 억제 규칙 적용
[미션 반응 수칙]                       ← 추가 (결과별 블록 하나)
```

환경 정보 목록에 **한 줄만** 넣고, 행동 지침은 별도 블록으로 분리합니다. 1학기에 프롬프트가 비대해져 503을 맞은 이력이 있으므로 **블록당 공백 포함 450자 이내**(치환값 포함, 조건부 문장 제외)로 제한합니다. 아래 템플릿 원문은 `success` 약 350자 · `retry` 약 270자 · `fail` 약 160자이고, 참고 대사 2개를 치환하면 `success` 가 약 420자가 됩니다. 조건부 문장(3-3)이 모두 붙는 최악의 경우 약 580자입니다.

`{result_label}` 표기: `success` → `성공`, `retry` → `시간 초과(재시도 가능)`, `fail` → `보류`

### 3-2. 결과별 블록

#### `success`

```
[미션 반응 수칙 — 임무 성공]
- 임무: {mission_name} ({stage}단계)
- 대장님이 방금 한 일: {achievement}
1. 이번 응답의 주인공은 성공 축하다. 우주 수준으로 과장하되,
   길이가 아니라 단어의 스케일(은하·본부·초신성·기록)로 과장하라.
2. 대장님이 한 행동을 구체적으로 한 번 짚어라.
3. 45자 규칙은 예외 없이 지킨다. 느낌표는 1개까지.
4. 참고 대사(복사 금지, 변주할 것): "{success_a}" / "{success_b}"
5. led는 rainbow, vibe는 strong_double.
{emotion_softener}
{piggyback_rule}
```

#### `retry`

```
[미션 반응 수칙 — 시간 초과]
- 임무: {mission_name}
- 부족했던 신호: {shortfall}
1. "실패"라는 단어를 쓰지 마라. 부족했던 것은 센서 신호이지 대장님이 아니다.
2. 무엇이 부족했는지 센서 관점으로 한 구절, 다시 할지는 대장님이 고르게 하라.
3. 재촉하는 표현(빨리, 꼭, 반드시, 다시 해야)을 쓰지 마라.
4. 참고 대사(복사 금지): "{retry_a}" / "{retry_b}"
5. led는 dim_blue, vibe는 short.
```

#### `fail` (보류)

```
[미션 반응 수칙 — 임무 보류]
- 임무: {mission_name}
1. 보류를 담담히 접수하라. "실패", "아쉽다"를 쓰지 마라.
2. 이 임무를 다시 권하지 마라.
3. {fallback_line}
4. led는 dim_blue, vibe는 soft_continuous.
```

`{fallback_line}` — 대체 미션이 있으면 `실내 대체 임무 '{fallback_name}'을 한 구절로만 가볍게 언급해도 된다.`, 없으면 `대체 임무도 제안하지 마라. 쉬어도 된다는 뜻만 전하라.`

### 3-3. 조건부 문장

**`{emotion_softener}`** — `user_emotion` 이 `sad` / `fear` 일 때만 삽입

```
6. 대장님 감정이 {emotion}이다. 과장 톤을 한 단계 낮춰 따뜻하게 축하하라.
   축하 자체는 생략하지 마라.
```

성공은 이 서비스가 사용자에게 주는 가장 중요한 보상이라 **감정이 가라앉아 있어도 축하는 유지**합니다. 톤만 낮춥니다. HW 신호는 성공 신호 그대로입니다.

**`{piggyback_rule}`** — 항상 삽입 (4절)

```
7. 대장님 발화가 임무와 무관하면 그 말에 먼저 답하고, 축하는 뒤에 짧은 한 구절로 붙여라.
   둘 다 45자에 못 넣으면 축하를 빼고 JSON에 "mission_ack": false 를 넣어라.
```

### 3-4. 기존 환경 수칙과의 충돌 억제

미션 블록이 들어가는 턴에서는 기존 수칙 일부를 **끕니다.** 45자 안에 지시가 세 개 겹치면 전부 흐려집니다.

| 기존 수칙 | 억제 조건 | 이유 |
| --- | --- | --- |
| 1. 조도 ≤ 50 lux → 환기 권유 | `mission_id == m_solar_panel` 이거나 `mission_result == fail` | 태양광 미션 재시도 대사와 같은 말을 두 번 함. 보류 직후 다른 행동을 권하면 강요가 됨 |
| 2. 화창 + `sad` → 산책 유도 | `mission_result != none` 인 모든 턴 | 미션 반응 턴에 다른 미션을 얹지 않음 (페르소나 "재차 권유하지 않는다") |

### 3-5. 미션별 치환값

`{achievement}` 와 `{shortfall}` 은 LLM이 무엇을 칭찬하고 무엇을 짚을지 정하는 핵심 값입니다. `missions.py` 의 `Mission` 에 필드로 추가할 것을 제안합니다.

| `mission_id` | `{achievement}` | `{shortfall}` |
| --- | --- | --- |
| `m_warm_touch` | 키링을 손으로 감싸 온기를 전했다 | 온기 신호가 3초를 채우지 못함 |
| `m_engine_start` | 오빗의 머리를 두 번 두드려 깨웠다 | 두드림 신호가 두 번으로 잡히지 않음 |
| `m_solar_panel` | 커튼을 열어 기지에 햇빛을 들였다 | 광량이 충분히 오래 유지되지 않음 |
| `m_basecamp_100m` | 기지 밖 100m까지 걸어 나갔다 | 이동 거리가 100m에 못 미침 (`{distance_m}`m 기록) |
| `m_first_greeting` | 현지인에게 먼저 인사를 건넸다 | — (자가 보고라 `retry` 없음) |

### 3-6. 출력 JSON 확장

```json
{"speech": "…", "led": "rainbow", "vibe": "strong_double", "mission_ack": true}
```

- `mission_ack` 는 **미션 블록이 있는 턴에서만** 요구합니다. 없는 턴에서는 생략하고, 서버는 누락을 `true` 로 봅니다.
- `InteractResponse` 에 `mission_ack: bool | None` 추가가 필요합니다.
- `led` / `vibe` 는 LLM이 반환하더라도 **서버가 1절 HW 신호로 덮어씁니다.** 프롬프트에 값을 적는 것은 LLM이 대사 톤을 신호와 맞추게 하려는 것입니다.

---

## 4. 미션 완료가 다른 대화에 끼어들 때

`ai/prompts/missions.md` 마지막 절의 규칙을 템플릿으로 옮긴 것이 `{piggyback_rule}` 입니다.

| 사용자 발화 | 판정 | 응답 구성 | 예 (자수) |
| --- | --- | --- | --- |
| "됐어?", "했어!", 빈 발화 | 미션 관련 | 축하 전용 | `치직- 본부에 긴급 타전! 대장님이 기지에 태양을 들였습니다. 라저` (37) |
| "배고프다", "오늘 뭐 먹지" | 무관 | 사용자 응답 → 축하 한 구절 | `치직- 보급부터 챙기십시오! 태양광 임무도 성공입니다. 오버` (33) |
| 긴 질문, 고민 상담 | 무관 + 길다 | 사용자 응답만, `mission_ack=false` | 다음 턴에 축하 이월 (1회) |

관련/무관은 LLM이 판단합니다. 규칙 기반 판정은 오분류가 많고, 틀려도 이월 장치가 있어 손실이 작습니다.

---

## 5. 성공 반응 문형 설계 — 45자 안의 "우주 수준" 피드백

### 5-1. 글자 예산

| 구간 | 예산 | 비고 |
| --- | --- | --- |
| 여는 말 `치직- ` | 4 | 고정 |
| **감탄부** | 6~12 | 느낌표로 끝나는 짧은 한 구 |
| **내용부** | 12~20 | 행동 호명 또는 스케일 비유 |
| 호칭 `대장님` + 쉼표 | 0~5 | 감탄부나 내용부 어디든 한 번 |
| 닫는 말 ` 라저` / ` 오버` | 3 | 성공은 `라저` 권장 |
| **합계** | **33~40** | 45자까지 **5자 이상 여유**를 둡니다. LLM은 목표보다 길게 쓰는 경향이 있음 |

### 5-2. 과장은 길이가 아니라 단어의 스케일로

45자 안에서는 수식어를 쌓을 수 없습니다. **한 단어의 크기**를 키웁니다.

| 쓰는 것 | 쓰지 않는 것 |
| --- | --- |
| 스케일 명사 — 은하, 우주 전역, 본부, 초신성, 궤도, 탐사 일지 | 형용사 중첩 — "정말 너무너무 대단하고 멋진" |
| 수치 과장 — 출력 200%, 광량 최고치, 기록 경신 | 감탄사 연발 — "와아! 우와! 대박!" |
| 본부 보고 형식 — 긴급 타전, 기록합니다 | 3문장 이상 나열 |
| 느낌표 1개 | 느낌표 2개 이상, 이모지 |

### 5-3. 문형 5종

LLM에 문형 이름을 지시하지 않습니다. 참고 대사와 수칙만 주고 LLM이 고르게 둡니다. 아래는 **6주차 회귀 테스트의 톤 기준**이자 E2E 합격 판정 기준입니다.

| 문형 | 구조 | 예 | 자수 |
| --- | --- | --- | --- |
| **A. 본부 타전형** | 보고 동사 + 대장님 행동 | `치직- 본부에 긴급 타전! 대장님이 기지에 태양을 들였습니다. 라저` | 37 |
| **B. 수치 폭증형** | 감탄 + 수치 과장 | `치직- 긴급 타전! 대장님 온기로 회로 출력 200% 돌파. 라저` | 36 |
| **C. 스케일 비유형** | 우주 스케일 비유 + 결과 | `치직- 은하 전역에 빛이 번집니다! 기지 광량 최고치, 대장님. 라저` | 38 |
| **D. 행동 호명형** | 행동 확인 + 덕분에 | `치직- 커튼 개방 확인! 대장님 덕에 태양 에너지 만땅입니다. 라저` | 37 |
| **E. 온기형** (`sad`/`fear`) | 과장 없이 따뜻한 인정 | `치직- 햇빛이 들어왔네요. 대장님, 정말 잘하셨습니다. 라저` | 33 |

E형은 느낌표를 쓰지 않습니다. 스케일 단어를 쓴다면 하나만 씁니다 (예: `치직- 온기 잘 받았어요, 대장님. 제 회로가 반짝입니다. 라저` — 35자).

### 5-4. 재시도·보류 문형

| 결과 | 구조 | 예 | 자수 |
| --- | --- | --- | --- |
| `retry` | 센서 관점의 부족 + 선택권 | `치직- 광량이 아직 부족합니다. 편하실 때 다시 열어 주십시오. 오버` | 38 |
| `retry` | 〃 | `치직- 온기 신호가 짧았습니다. 원하시면 한 번 더 쥐어 주십시오. 오버` | 40 |
| `fail` | 담담한 접수 + 기록 | `치직- 임무 보류 접수. 기록은 안전하게 보관합니다. 교신 종료` | 35 |
| `fail` | 쉬어도 된다는 허락 | `치직- 알겠습니다. 오늘은 쉬어 가도 괜찮습니다. 교신 종료` | 33 |

### 5-5. 금지어

| 결과 | 금지 | 이유 |
| --- | --- | --- |
| 전체 | `실패` | 4주차 원칙. 상태 이름에도 쓰지 않음 |
| `retry` | `빨리`, `꼭`, `반드시`, `다시 해야`, `왜` | 재촉·추궁 |
| `fail` | `아쉽`, `다음엔 꼭`, 같은 미션 재언급 | 재권유 |
| `success` + `sad`/`fear` | 느낌표 2개 이상, `최고`, `대박` | 감정 온도차 |

금지어는 6주차 회귀 테스트에서 자동 검사 항목으로 씁니다.

---

## 6. 적용 스케치 (참고용 — 이번 주 코드 변경 없음)

```python
# ai/app/core/context.py

RESULT_LABEL = {
    MissionResult.SUCCESS: "성공",
    MissionResult.RETRY: "시간 초과(재시도 가능)",
    MissionResult.FAIL: "보류",
}


def build_system_prompt(emotion: Emotion, ctx: EnvContext) -> str:
    mission = BY_ID.get(ctx.mission_id) if ctx.mission_result is not MissionResult.NONE else None
    ...
    if mission:
        parts.append(f"- 미션 교신: {mission.name} → {RESULT_LABEL[ctx.mission_result]}")

    parts.append("\n[환경별 컨텍스트 제어 수칙]")
    suppress_lux = mission and (
        mission.mission_id == "m_solar_panel" or ctx.mission_result is MissionResult.FAIL
    )
    if ctx.lux is not None and ctx.lux <= 50 and not suppress_lux:
        ...
    if ctx.weather and emotion is Emotion.SAD and not mission:
        ...

    if mission:
        parts.append(build_mission_block(mission, ctx.mission_result, emotion))
```

```python
# ai/app/core/pipeline.py — LLM 응답 후

MISSION_SIGNAL = {
    MissionResult.SUCCESS: SIGNAL_SUCCESS,
    MissionResult.RETRY: SIGNAL_TIMEOUT,
    MissionResult.FAIL: SIGNAL_DEFERRED,
}

if not result.fallback_triggered:
    sig = MISSION_SIGNAL.get(ctx.mission_result)
    if sig:
        result.led, result.vibe, result.oled_expression = sig.led, sig.vibe, sig.oled
    else:
        result.oled_expression = oled_for(emotion)
```

고위험 발화 턴에서는 미션 블록을 포함한 모든 주입이 무시됩니다 (LLM을 호출하지 않음). 미션 결과는 **소비하지 않은 것으로** 두고 다음 턴으로 이월합니다.

---

## 7. 미확정 항목

| # | 항목 | 담당 | 비고 |
| --- | --- | --- | --- |
| 1 | `interact.py` 에 `mission_result` 파라미터 추가 | AI | **E2E 선결 조건.** 0절 1번 |
| 2 | 백엔드 대기열·1회 소비·10분 만료 | 백엔드 | 2절 |
| 3 | `mission_ack` 필드 추가 | AI · 백엔드 | 3-6 |
| 4 | `fail` → `deferred` 이름 변경 | AI · 백엔드 | 6주차 인터페이스 v2 |
| 5 | `achievement` / `shortfall` 필드를 `missions.py` 에 추가 | AI | 3-5 |
| 6 | 미션 반응 턴의 레이턴시 | AI | 블록 추가로 프롬프트가 약 160~580자 늘어남. 재측정은 API 키가 있는 환경에서 |
