"""응답 음성 형식 테스트.

키링(hw/Orbit/audio_out)은 PCM 16bit · 16000Hz WAV만 재생합니다.
edge-tts 는 네트워크가 필요하므로 가짜로 바꾸고, 변환·저장 경로만 확인합니다.
ffmpeg 가 없으면(pydub 디코딩 불가) 건너뜁니다.
"""

import asyncio
import io
import sys
import types
import wave
from shutil import which

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(which("ffmpeg") is None, reason="ffmpeg 필요 (pydub)")


def _fake_edge_tts(monkeypatch, frame_rate=24000, channels=1):
    """edge-tts 대신 1초짜리 사인파 음성을 '_raw.mp3' 경로에 씁니다 (내용은 WAV)."""
    import numpy as np

    t = np.linspace(0, 1, frame_rate, endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t) * 8000).astype(np.int16)
    if channels == 2:
        tone = np.repeat(tone, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(frame_rate)
        w.writeframes(tone.tobytes())
    data = buf.getvalue()

    class Communicate:
        def __init__(self, text, voice, rate=None):
            pass

        async def save(self, path):
            with open(path, "wb") as f:
                f.write(data)

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=Communicate))


@pytest.mark.parametrize("plain", [False, True])
@pytest.mark.parametrize("frame_rate, channels", [(24000, 1), (44100, 2)])
def test_output_is_16k_mono_16bit_pcm_wav(tmp_path, monkeypatch, plain, frame_rate, channels):
    """무전 톤 경로와 고위험 응답 경로(plain) 모두 키링 재생 형식이어야 합니다."""
    from app.core.tts import RadioTTS

    _fake_edge_tts(monkeypatch, frame_rate, channels)
    out = tmp_path / "reply.wav"
    returned = asyncio.run(RadioTTS().synthesize("치직- 테스트입니다. 오버", str(out), plain=plain))

    assert returned == str(out)
    with wave.open(str(out), "rb") as w:
        assert w.getframerate() == 16000
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getcomptype() == "NONE"  # PCM
        assert w.getnframes() > 16000 * 0.9  # 약 1초 이상 (무전 노이즈 포함 시 더 김)
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    assert list(tmp_path.iterdir()) == [out]  # 중간 파일(_raw.mp3)은 남기지 않음

    # 피크가 -1dBFS 근처로 정규화됨 (입력 사인파는 약 -12dBFS)
    peak_dbfs = 20 * np.log10(np.abs(samples.astype(np.int32)).max() / 32768)
    assert -1.5 <= peak_dbfs <= -0.5, peak_dbfs


def test_silence_is_not_amplified():
    """무음은 정규화해도 무음이어야 합니다 (0으로 나누기·잡음 증폭 없음)."""
    from pydub import AudioSegment

    from app.core.tts import to_keyring_wav

    out = to_keyring_wav(AudioSegment.silent(duration=500, frame_rate=24000))
    assert out.frame_rate == 16000 and out.channels == 1 and out.sample_width == 2
    assert out.max == 0


def test_raw_file_removed_when_conversion_fails(tmp_path, monkeypatch):
    class Broken:
        def __init__(self, *a, **k):
            pass

        async def save(self, path):
            with open(path, "wb") as f:
                f.write(b"not audio")

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=Broken))
    from app.core.tts import RadioTTS

    with pytest.raises(Exception):
        asyncio.run(RadioTTS().synthesize("테스트", str(tmp_path / "x.wav")))
    assert list(tmp_path.iterdir()) == []
