"""텍스트 → 무전 톤 음성.

파이프라인: edge-tts(ko-KR-InJoonNeural, rate +10%)
            → low_pass 3000Hz + high_pass 300Hz (무전기 대역)
            → 앞뒤에 화이트 노이즈("치직-") 합성

⚠️ 기능 복원: 1학기 노트북의 OrbitAdvancedVoice(cell-2)에는 노이즈 합성이
   있었지만, 실제로 파이프라인에서 쓰인 OrbitCoreV4.speak()에는 빠져 있었습니다
   (`final_audio = voice`). 노션 2주차 일지가 기술한 동작은 전자이므로
   여기서는 노이즈 합성을 포함한 버전으로 복원했습니다.

출력 형식: 16kHz · 모노 · 16bit PCM WAV (11-13 변경, 이전 mp3).
   음량 (11-13): 키링 스피커에서 소리가 작아, 목소리를 -1dBFS 로 정규화한 뒤
   피크 리미터로 평균 음량을 키웁니다. 피크 정규화만으로는 약 +4dB 밖에 안
   커져서 부족했습니다. 앞뒤 노이즈는 목소리보다 작게 맞춥니다.
   처음에는 tanh 로 파형을 직접 눌렀는데 목소리가 거칠어져서, 파형은 그대로 두고
   음량(게인)만 부드럽게 줄이는 엔벨로프 방식으로 바꿨습니다.
   키링(ESP32)은 mp3를 디코딩하지 못하고, audio_out 이 16kHz PCM 16bit WAV만
   재생합니다. 고위험 응답(plain=True)도 같은 형식으로 내보냅니다.

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

LOW_PASS_HZ = 3000
HIGH_PASS_HZ = 300

# 키링 재생 형식 (hw/Orbit/audio_out: PCM 16bit, 16000Hz만 재생)
OUT_SAMPLE_RATE = 16000
OUT_CHANNELS = 1
OUT_SAMPLE_WIDTH = 2  # bytes = 16bit

# ─── 음량 (11-13) ─────────────────────────────────────────────
# 최대 피크. 0dBFS 에 붙이지 않는 건 클리핑 여유.
TARGET_PEAK_DBFS = -1.0
# 리미터 설정. 구동량이 클수록 커지지만 일정 이상에서는 거의 안 커지고 거칠어집니다.
# 11-13 실측(동일 문장, 무전 톤): 정규화만 RMS -20.0dBFS → 이 설정 -13.8dBFS,
#   파형 왜곡 SDR 21dB (이전 tanh 12dB 방식은 -11.4dBFS 였지만 SDR 13.8dB 로 거칠었음)
LIMITER_DRIVE_DB = 12.0
LIMITER_LOOKAHEAD_MS = 3.0  # 피크 직전부터 미리 줄여 순간 클리핑 방지
LIMITER_RELEASE_MS = 40.0   # 줄인 음량을 되돌리는 속도. 짧을수록 커지고 거칠어짐
# 앞뒤 노이즈 음량 (목소리 RMS 기준). 이전에는 노이즈가 목소리보다 커서 목소리를 가렸습니다.
STATIC_PRE_BELOW_VOICE_DB = 6.0
STATIC_POST_BELOW_VOICE_DB = 8.0


def to_keyring_wav(segment):
    """pydub AudioSegment 를 키링 재생 형식(16kHz 모노 16bit)으로 바꾸고 피크를 -1dBFS 로 맞춥니다.

    리샘플링 뒤에 정규화합니다. 순서를 바꾸면 리샘플링으로 피크가 달라져
    목표치에서 벗어날 수 있습니다.
    """
    from pydub.effects import normalize

    converted = (
        segment.set_frame_rate(OUT_SAMPLE_RATE)
        .set_channels(OUT_CHANNELS)
        .set_sample_width(OUT_SAMPLE_WIDTH)
    )
    return normalize(converted, headroom=-TARGET_PEAK_DBFS)


def limit_loudness(
    segment,
    drive_db: float = LIMITER_DRIVE_DB,
    lookahead_ms: float = LIMITER_LOOKAHEAD_MS,
    release_ms: float = LIMITER_RELEASE_MS,
):
    """drive_db 만큼 키우고, 피크가 -1dBFS 를 넘는 구간만 음량을 부드럽게 줄입니다 (피크 리미터).

    파형을 직접 깎지 않고 게인만 바꾸기 때문에 tanh·클리핑보다 소리가 덜 거칩니다.
      1. 샘플마다 피크를 넘지 않는 데 필요한 게인을 구함
      2. lookahead 구간의 최솟값을 미리 적용 (피크 전에 줄여 둠)
      3. 줄인 게인은 release 시간에 걸쳐 천천히 되돌림
      4. lookahead 길이로 평균 내서 게인 변화를 매끄럽게
    3·4는 값을 더 작게만 만들므로 결과 피크가 -1dBFS 를 넘지 않습니다.
    16bit 세그먼트(to_keyring_wav 결과)를 받습니다.
    """
    from numpy.lib.stride_tricks import sliding_window_view

    sr = segment.frame_rate
    ceiling = 10 ** (TARGET_PEAK_DBFS / 20)
    x = np.array(segment.get_array_of_samples(), dtype=np.float64) / 32768.0
    if x.size == 0:
        return segment
    x *= 10 ** (drive_db / 20)

    need = np.minimum(1.0, ceiling / np.maximum(np.abs(x), 1e-12))
    look = max(1, int(sr * lookahead_ms / 1000))
    gain = sliding_window_view(np.concatenate([need, np.ones(look)]), look + 1).min(axis=1)

    alpha = 1.0 - np.exp(-1.0 / (sr * release_ms / 1000))
    released = np.empty_like(gain)
    g = 1.0
    for i, target in enumerate(gain):
        g = target if target < g else g + (target - g) * alpha
        released[i] = g

    smooth = np.convolve(
        np.concatenate([np.full(look, released[0]), released]),
        np.ones(look + 1) / (look + 1),
        mode="valid",
    )
    y = np.clip(x * smooth, -ceiling, ceiling)
    return segment._spawn((y * 32767).astype(np.int16).tobytes())


class RadioTTS:
    def __init__(self) -> None:
        self._settings = get_settings()

    def _create_static(self, duration_ms: int, rms_dbfs: float):
        """치직- 하는 무전기 화이트 노이즈를 키링 재생 형식으로 생성합니다.

        rms_dbfs: 노이즈의 평균 음량(RMS, dBFS). 균일 분포라 피크는 RMS보다 약 4.8dB 큽니다.
        """
        from pydub import AudioSegment

        n = int(OUT_SAMPLE_RATE * (duration_ms / 1000.0))
        amp = min(1.0, 10 ** (rms_dbfs / 20) * np.sqrt(3))
        samples = (np.random.uniform(-1, 1, n) * amp * 32767).astype(np.int16)
        return AudioSegment(
            samples.tobytes(), frame_rate=OUT_SAMPLE_RATE,
            sample_width=OUT_SAMPLE_WIDTH, channels=OUT_CHANNELS,
        )

    async def synthesize(self, text: str, out_path: str, plain: bool = False) -> str:
        """out_path 에 16kHz 모노 16bit WAV 를 쓰고 그 경로를 돌려줍니다.

        plain=True 이면 무전 톤 후처리(대역 필터 + 노이즈 합성)를 건너뜁니다.
        고위험 발화 대응 시에만 씁니다. 위기 상황에서 캐릭터 연출을 하지
        않기 위함입니다. → docs/high-risk-utterance-policy.md
        형식 변환과 음량 처리(정규화 + 리미터)는 plain 여부와 관계없이 합니다.
        """
        import edge_tts
        from pydub import AudioSegment

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        raw = out.with_name(out.stem + "_raw.mp3")

        try:
            communicate = edge_tts.Communicate(text, self._settings.tts_voice, rate="+10%")
            await communicate.save(str(raw))

            voice = AudioSegment.from_file(raw)
            if plain:
                final = limit_loudness(to_keyring_wav(voice))
            else:
                filtered = voice.low_pass_filter(LOW_PASS_HZ).high_pass_filter(HIGH_PASS_HZ)
                loud = limit_loudness(to_keyring_wav(filtered))
                level = loud.dBFS  # 목소리 평균 음량(RMS)
                final = (
                    self._create_static(400, level - STATIC_PRE_BELOW_VOICE_DB)
                    + loud
                    + self._create_static(600, level - STATIC_POST_BELOW_VOICE_DB)
                )

            final.export(out, format="wav")
        finally:
            raw.unlink(missing_ok=True)
        return str(out)
