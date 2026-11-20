r"""키링 비상 음성 WAV 생성 (11-20 HW 요청).

키링이 AI 서버에 아예 연결하지 못할 때 펌웨어에서 직접 재생할 음성입니다.
Gemini 만 실패한 경우에는 서버의 EMERGENCY_RESPONSE 가 같은 대사를 보내므로,
두 경우에 같은 목소리·같은 대사가 나오도록 평소 응답과 같은 TTS 설정
(ko-KR-InJoonNeural, +10%, 무전 필터, 음량 리미터)으로 만듭니다.

형식: WAV 16kHz 모노 16bit PCM, 5초 이내 (펌웨어 용량)
평소 경로 그대로면 edge-tts 가 마침표마다 1초 넘게 쉬어서 약 9초가 됩니다.
그래서 이 파일만 문장 사이 쉬는 구간을 짧게 줄이고, 앞뒤 노이즈도 짧게 둡니다.
말소리 자체(속도·음색)는 평소 응답과 같습니다.

실행 (ai/ 에서):
    .venv\Scripts\python -m tools.make_emergency_wav
"""

from __future__ import annotations

import asyncio
import tempfile
import wave
from pathlib import Path

from app.core.llm import EMERGENCY_RESPONSE
from app.core.tts import (
    HIGH_PASS_HZ,
    LOW_PASS_HZ,
    STATIC_POST_BELOW_VOICE_DB,
    STATIC_PRE_BELOW_VOICE_DB,
    RadioTTS,
    limit_loudness,
    to_keyring_wav,
)

OUT = Path(__file__).resolve().parents[1] / "assets" / "emergency.wav"
MAX_SECONDS = 5.0
KEEP_SILENCE_MS = 90   # 말소리 앞뒤로 남기는 무음 → 문장 사이 약 0.18초
STATIC_PRE_MS = 300    # 평소 400
STATIC_POST_MS = 400   # 평소 600


async def build() -> None:
    import edge_tts
    from pydub import AudioSegment
    from pydub.silence import split_on_silence

    tts = RadioTTS()
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.mp3"
        await edge_tts.Communicate(
            EMERGENCY_RESPONSE.speech, tts._settings.tts_voice, rate="+10%"
        ).save(str(raw))
        voice = AudioSegment.from_file(raw)

    chunks = split_on_silence(
        voice, min_silence_len=150, silence_thresh=voice.dBFS - 16, keep_silence=KEEP_SILENCE_MS
    )
    tight = sum(chunks[1:], chunks[0])

    filtered = tight.low_pass_filter(LOW_PASS_HZ).high_pass_filter(HIGH_PASS_HZ)
    loud = limit_loudness(to_keyring_wav(filtered))
    level = loud.dBFS
    final = (
        tts._create_static(STATIC_PRE_MS, level - STATIC_PRE_BELOW_VOICE_DB)
        + loud
        + tts._create_static(STATIC_POST_MS, level - STATIC_POST_BELOW_VOICE_DB)
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    final.export(OUT, format="wav")


def main() -> None:
    asyncio.run(build())
    with wave.open(str(OUT)) as w:
        sec = w.getnframes() / w.getframerate()
        fmt = (w.getframerate(), w.getnchannels(), w.getsampwidth() * 8, w.getcomptype())
    print(f"{OUT} | {fmt[0]}Hz {fmt[1]}ch {fmt[2]}bit {fmt[3]} | {sec:.2f}s | {OUT.stat().st_size} bytes")
    if fmt != (16000, 1, 16, "NONE") or sec > MAX_SECONDS:
        raise SystemExit(f"요구 형식(16kHz 모노 16bit PCM, {MAX_SECONDS}초 이내)과 다릅니다")


if __name__ == "__main__":
    main()
