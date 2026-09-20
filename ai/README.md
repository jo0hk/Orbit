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

**골격만 있습니다.** 각 모듈의 `NotImplementedError`와 `TODO(1주차)` 주석이
Colab 노트북에서 옮겨와야 할 지점입니다. 이식 순서:

1. `llm.py` — Gemini 호출 + tenacity 백오프
2. `tts.py` — edge-tts + 무전 노이즈 (`nest_asyncio` 패치는 제거)
3. `stt.py` — faster-whisper로 교체하며 이식
4. `emotion.py` — 모델 정의 + 가중치 로딩
5. `vision.py` — 멀티모달 호출

각 단계마다 `/health`와 최소 요청으로 확인하고 넘어가세요.

## 레이턴시 기준선

1학기 최종 **6초대** (최초 10.51초). `InteractResponse.latency`가 단계별
소요 시간을 담습니다. 미션 판정이 붙는 5주차 이후 이 값을 계속 감시하세요.

Colab T4 GPU에서 측정한 값이므로, 서버 CPU 환경에서 STT 단독 시간을
다시 재고 기록해야 합니다.

## 주의

- **`max_output_tokens`로 출력을 자르지 마세요.** JSON이 깨져 `ServerError`가
  납니다. 글자 수 제한은 프롬프트의 45자 규칙으로 겁니다.
- **`gTTS`로 되돌리지 마세요.** click/typer 의존성 충돌로 폐기했습니다.
- **감정 5클래스에 긍정이 없습니다.** 미션 성공 칭찬을 감정 엔진이 받쳐주지
  못합니다. 1주차 결정 사항입니다.
