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

    # 피크가 -1dBFS 근처, 넘지는 않음 (입력 사인파는 약 -12dBFS → 정규화 + 리미터)
    peak_dbfs = 20 * np.log10(np.abs(samples.astype(np.int32)).max() / 32768)
    assert -1.5 <= peak_dbfs <= -0.5, peak_dbfs


def test_limiter_raises_loudness_and_keeps_peak():
    """리미터는 평균 음량을 키우되 피크는 -1dBFS 를 넘기지 않아야 합니다."""
    from pydub import AudioSegment

    from app.core.tts import limit_loudness, to_keyring_wav

    sr = 16000
    t = np.linspace(0, 1, sr, endpoint=False)
    # 말소리처럼 크고 작은 구간이 섞인 신호 (평균은 작고 피크만 큼)
    x = np.sin(2 * np.pi * 300 * t) * (0.05 + 0.95 * (t > 0.9))
    seg = AudioSegment((x * 20000).astype(np.int16).tobytes(), frame_rate=sr, sample_width=2, channels=1)

    base = to_keyring_wav(seg)
    loud = limit_loudness(base, 12.0)
    b = np.array(base.get_array_of_samples(), dtype=np.float64)
    l = np.array(loud.get_array_of_samples(), dtype=np.float64)
    assert 20 * np.log10(np.abs(l).max() / 32768) <= -1.0 + 1e-6  # 피크는 넘지 않음
    quiet = slice(0, int(0.9 * sr))
    gain_quiet = 20 * np.log10(np.sqrt(np.mean(l[quiet] ** 2)) / np.sqrt(np.mean(b[quiet] ** 2)))
    assert gain_quiet > 10.0  # 작은 소리는 거의 구동량(12dB)만큼 커짐


def test_limiter_keeps_waveform_clean():
    """큰 소리도 파형을 깎지 않고 음량만 줄여야 합니다 (11-13: tanh 방식이 거칠어 교체).

    일정한 큰 사인파를 넣으면, 줄어든 크기의 사인파가 그대로 나와야 합니다.
    파형을 깎는 방식(tanh, 클리핑)으로 되돌아가면 이 테스트가 실패합니다.
    """
    from pydub import AudioSegment

    from app.core.tts import limit_loudness, to_keyring_wav

    sr = 16000
    t = np.linspace(0, 1, sr, endpoint=False)
    x = np.sin(2 * np.pi * 400 * t)
    seg = to_keyring_wav(AudioSegment((x * 20000).astype(np.int16).tobytes(), frame_rate=sr, sample_width=2, channels=1))
    y = np.array(limit_loudness(seg, 12.0).get_array_of_samples(), dtype=np.float64)

    body = slice(int(0.1 * sr), int(0.9 * sr))  # 시작부 게인 변화 구간 제외
    ref = x[body]
    g = (ref @ y[body]) / (ref @ ref)
    residual = y[body] - g * ref
    sdr_db = 10 * np.log10(np.sum(y[body] ** 2) / np.sum(residual ** 2))
    assert sdr_db > 35.0, sdr_db


def test_radio_static_quieter_than_voice(tmp_path, monkeypatch):
    """앞뒤 노이즈가 목소리를 가리지 않도록 목소리보다 작아야 합니다."""
    from app.core.tts import RadioTTS

    _fake_edge_tts(monkeypatch)
    out = tmp_path / "reply.wav"
    asyncio.run(RadioTTS().synthesize("테스트", str(out)))
    with wave.open(str(out), "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    rms = lambda s: np.sqrt(np.mean(s ** 2))
    pre, voice, post = a[: int(0.4 * 16000)], a[int(0.4 * 16000): -int(0.6 * 16000)], a[-int(0.6 * 16000):]
    assert rms(pre) < rms(voice)
    assert rms(post) < rms(pre)


def test_silence_is_not_amplified():
    """무음은 정규화해도 무음이어야 합니다 (0으로 나누기·잡음 증폭 없음)."""
    from pydub import AudioSegment

    from app.core.tts import to_keyring_wav

    from app.core.tts import limit_loudness

    out = to_keyring_wav(AudioSegment.silent(duration=500, frame_rate=24000))
    assert out.frame_rate == 16000 and out.channels == 1 and out.sample_width == 2
    assert out.max == 0
    assert limit_loudness(out, 12.0).max == 0


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
