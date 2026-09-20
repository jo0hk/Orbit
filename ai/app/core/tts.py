"""텍스트 → 무전 톤 음성.

파이프라인: edge-tts(ko-KR-InJoonNeural, rate +10%)
            → low_pass 3000Hz + high_pass 300Hz (무전기 대역)
            → 앞뒤에 화이트 노이즈("치직-") 합성

⚠️ 기능 복원: 1학기 노트북의 OrbitAdvancedVoice(cell-2)에는 노이즈 합성이
   있었지만, 실제로 파이프라인에서 쓰인 OrbitCoreV4.speak()에는 빠져 있었습니다
   (`final_audio = voice`). 노션 2주차 일지가 기술한 동작은 전자이므로
   여기서는 노이즈 합성을 포함한 버전으로 복원했습니다.

⚠️ pydub은 ffmpeg 바이너리가 필요합니다.
⚠️ nest_asyncio는 Colab 주피터 전용이라 제거했습니다. FastAPI는 자체
   이벤트 루프를 돌리므로 패치하면 오히려 깨집니다.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100
LOW_PASS_HZ = 3000
HIGH_PASS_HZ = 300


class RadioTTS:
    def __init__(self) -> None:
        self._settings = get_settings()

    def _create_static(self, duration_ms: int, volume_db: int):
        """치직- 하는 무전기 화이트 노이즈를 수학적으로 생성합니다."""
        from pydub import AudioSegment

        n = int(SAMPLE_RATE * (duration_ms / 1000.0))
        samples = (np.random.uniform(-1, 1, n) * 32767).astype(np.int16)
        segment = AudioSegment(
            samples.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=1
        )
        return segment + volume_db

    async def synthesize(self, text: str, out_path: str) -> str:
        """returns 생성된 음성 파일 경로."""
        import edge_tts
        from pydub import AudioSegment

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        raw = out.with_name(out.stem + "_raw.mp3")

        communicate = edge_tts.Communicate(text, self._settings.tts_voice, rate="+10%")
        await communicate.save(str(raw))

        voice = AudioSegment.from_file(raw, format="mp3")
        filtered = voice.low_pass_filter(LOW_PASS_HZ).high_pass_filter(HIGH_PASS_HZ)

        final = self._create_static(400, -15) + filtered + self._create_static(600, -20)
        final.export(out, format="mp3")

        raw.unlink(missing_ok=True)
        return str(out)
