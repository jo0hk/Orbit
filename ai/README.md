# Orbit AI Server

우주탐사대원 오빗의 AI 파트. 음성을 받아 감정과 환경을 분석하고,
페르소나를 유지한 응답과 하드웨어 제어 신호를 함께 반환합니다.

```
STT ➡️ 감정 분석 ➡️ 환경 분석 ➡️ LLM ➡️ TTS
```

## 구조

| 경로 | 역할 | 1학기 출처 |
| --- | --- | --- |
| `app/main.py` | FastAPI 엔트리 | 5주차 |
| `app/schemas.py` | 파트 간 공유 계약 (감정 라벨, HW enum) | 1주차 확정 예정 |
| `app/core/stt.py` | 음성 → 텍스트 | 2주차 (Whisper → faster-whisper 교체) |
| `app/core/emotion.py` | 멀티모달 감정 분류 | 3주차 (Accuracy 97.33%) |
| `app/core/context.py` | 환경 컨텍스트 주입 | 4주차 |
| `app/core/llm.py` | Gemini 2.5 Flash, Strict JSON | 2주차 |
| `app/core/tts.py` | 무전 톤 음성 합성 | 2주차 |
| `app/core/vision.py` | 탐사 인증샷 칭찬 | 4주차 |
| `app/core/pipeline.py` | 오케스트레이션 + 레이턴시 측정 | — |
| `prompts/persona.md` | 오빗 시스템 프롬프트 | 1주차 |

`models/`에는 감정 모델 가중치가 들어가며 git에 커밋되지 않습니다.

## 실행

```bash
# PyTorch는 CPU 전용 휠로 먼저 (기본 설치는 CUDA 포함 2GB+)
pip install torch --index-url https://download.pytorch.org/whl/cpu

python -m venv .venv && source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # 키 입력

uvicorn app.main:app --reload --port 8000
```

`pydub`의 `low_pass_filter`에는 ffmpeg 바이너리가 필요합니다.

## 현재 상태

1학기 Colab 노트북(`Orbit.ipynb`)의 코드를 **이식 완료**했습니다. 다만 아직
실행 검증은 하지 않았습니다. 구문 검사만 통과한 상태입니다.

이식하며 원본과 달라진 점:

| 항목 | 1학기 노트북 | 현재 | 이유 |
| --- | --- | --- | --- |
| STT 엔진 | openai-whisper | faster-whisper | CPU 추론 약 4배 |
| STT initial_prompt | cell-1에만 있음 | 복원 | 고유명사 인식률 |
| TTS 노이즈 합성 | cell-2에만 있음 | 복원 | 노션 문서와 일치시킴 |
| 오디오 특징 실패 | bare except로 무시 | 경고 로깅 | 조용한 실패 방지 |
| 감정 라벨 검증 | 없음 | 기동 시 대조 | 체크포인트 불일치 조기 발견 |
| 감정 신뢰도 | 없음 | softmax 추가 | 2주차 로그 필드 |
| nest_asyncio | 적용 | 제거 | Colab 전용 |
| 마이크 녹음 | Colab JS 브릿지 | 제거 | 앱이 녹음해 전송 |

## 첫 실행 전 확인

1. `ai/models/orbit_emotion_v1.pth` 가 있는지 (드라이브에서 내려받아 배치)
2. `ai/.env` 의 `GEMINI_API_KEY` 가 비어 있지 않은지
   → 1학기에 빈 키로 돌려서 모든 LLM 호출이 실패했습니다
3. ffmpeg 설치 여부 (`ffmpeg -version`)

## 레이턴시 기준선

**아직 없습니다.**

1학기 일지의 "6초대"는 유효한 측정값이 아닙니다. 해당 벤치마크(cell-9)가
실행될 때 `API_KEY=""` 라 Gemini 호출이 모두 실패했고, tenacity가
`wait_exponential(min=2, max=8)`로 3회 재시도하며 약 6초를 대기했습니다.
기록된 6.72초는 사실상 그 대기 시간입니다.

1주차에 정상 응답 기준으로 다시 측정하세요. `InteractResponse.latency`가
STT / 감정 / LLM / TTS 단계별 소요 시간을 담습니다.

## 주의

- **`max_output_tokens`로 출력을 자르지 마세요.** JSON이 깨져 `ServerError`가
  납니다. 글자 수 제한은 프롬프트의 45자 규칙으로 겁니다.
- **`gTTS`로 되돌리지 마세요.** click/typer 의존성 충돌로 폐기했습니다.
- **`nest_asyncio.apply()`를 다시 넣지 마세요.** FastAPI 이벤트 루프와 충돌합니다.
- **감정 5클래스에 긍정이 없습니다.** 미션 성공 칭찬을 감정 엔진이 받쳐주지
  못합니다. 1주차 결정 사항입니다.
- **Gemini safety_settings가 4개 카테고리 전부 `BLOCK_NONE`입니다.**
  1학기 설정을 그대로 옮겼으나, `DANGEROUS_CONTENT`까지 열려 있어 3주차
  고위험 발화 대응 정책과 충돌합니다. `core/llm.py`의 TODO를 보세요.
- **Gemini 무료 티어는 일 20요청입니다.** 1학기에 429로 비전 테스트가
  중단됐습니다. E2E 테스트를 반복할 계획이면 할당량을 먼저 확인하세요.
