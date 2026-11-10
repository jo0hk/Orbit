#include "audio_out.h"
#include <driver/i2s.h>
#include <esp_idf_version.h>

#define SPK_PORT   I2S_NUM_1   // 마이크(I2S_NUM_0)와 분리
#define FRAMES     256

static bool spkReady = false;
static int16_t outBuf[FRAMES * 2];   // 스테레오 프레임

bool audioOutBegin() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
  cfg.sample_rate = REC_SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 6;
  cfg.dma_buf_len = FRAMES;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = true;   // 데이터가 없으면 무음 -> 앰프 잡음 방지

  i2s_pin_config_t pins = {};
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(4, 4, 0)
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
#endif
  pins.bck_io_num = SPK_BCLK_PIN;
  pins.ws_io_num = SPK_LRC_PIN;
  pins.data_out_num = SPK_DIN_PIN;
  pins.data_in_num = I2S_PIN_NO_CHANGE;

  if (i2s_driver_install(SPK_PORT, &cfg, 0, nullptr) != ESP_OK) {
    Serial.println("[AudioOut] I2S 설치 실패");
    return false;
  }
  if (i2s_set_pin(SPK_PORT, &pins) != ESP_OK) {
    Serial.println("[AudioOut] I2S 핀 설정 실패");
    i2s_driver_uninstall(SPK_PORT);
    return false;
  }
  i2s_zero_dma_buffer(SPK_PORT);
  spkReady = true;
  return true;
}

static bool writeFrames(size_t frames) {
  size_t written = 0;
  return i2s_write(SPK_PORT, outBuf, frames * 2 * sizeof(int16_t), &written, pdMS_TO_TICKS(500)) == ESP_OK;
}

void audioOutTone(float freq, uint32_t ms, float volume) {
  if (!spkReady) return;
  uint32_t total = (uint32_t)REC_SAMPLE_RATE * ms / 1000;
  uint32_t fade = REC_SAMPLE_RATE / 100;   // 앞뒤 10ms 페이드 ('틱' 방지)
  float phase = 0, inc = 2.0f * PI * freq / REC_SAMPLE_RATE;

  for (uint32_t done = 0; done < total;) {
    uint32_t n = min((uint32_t)FRAMES, total - done);
    for (uint32_t i = 0; i < n; i++) {
      uint32_t pos = done + i;
      float env = 1.0f;
      if (pos < fade) env = (float)pos / fade;
      else if (total - pos < fade) env = (float)(total - pos) / fade;
      int16_t s = (int16_t)(sinf(phase) * 32767.0f * volume * env);
      outBuf[2 * i] = s;
      outBuf[2 * i + 1] = s;
      phase += inc;
      if (phase > 2.0f * PI) phase -= 2.0f * PI;
    }
    if (!writeFrames(n)) break;
    done += n;
  }
}

// len 바이트를 다 받을 때까지 읽기. 수신이 AUDIO_STREAM_TIMEOUT_MS 이상 끊기면 실패
static bool readExact(WiFiClient& in, uint8_t* buf, size_t len) {
  size_t got = 0;
  unsigned long last = millis();
  while (got < len) {
    int avail = in.available();
    if (avail > 0) {
      int r = in.read(buf + got, min((size_t)avail, len - got));
      if (r > 0) { got += r; last = millis(); }
    } else {
      if (!in.connected() || millis() - last > AUDIO_STREAM_TIMEOUT_MS) return false;
      vTaskDelay(1);
    }
  }
  return true;
}

static bool skipBytes(WiFiClient& in, uint32_t len) {
  uint8_t tmp[64];
  while (len > 0) {
    uint32_t n = min((uint32_t)sizeof(tmp), len);
    if (!readExact(in, tmp, n)) return false;
    len -= n;
  }
  return true;
}

static uint32_t le32(const uint8_t* p) { return p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24); }
static uint16_t le16(const uint8_t* p) { return p[0] | (p[1] << 8); }

bool audioOutPlayWav(WiFiClient& in, volatile bool* stopFlag) {
  if (!spkReady) return false;

  // 1) RIFF 헤더
  uint8_t hdr[12];
  if (!readExact(in, hdr, 12) || memcmp(hdr, "RIFF", 4) != 0 || memcmp(hdr + 8, "WAVE", 4) != 0) {
    Serial.println("[AudioOut] WAV 파일이 아님 (mp3면 재생 불가)");
    return false;
  }

  // 2) fmt / data 청크 찾기
  uint16_t channels = 0, bits = 0;
  uint32_t sampleRate = 0, dataSize = 0;
  while (true) {
    uint8_t ch[8];
    if (!readExact(in, ch, 8)) return false;
    uint32_t size = le32(ch + 4);
    if (memcmp(ch, "fmt ", 4) == 0) {
      uint8_t fmt[16];
      if (size < 16 || !readExact(in, fmt, 16)) return false;
      uint16_t format = le16(fmt);
      channels = le16(fmt + 2);
      sampleRate = le32(fmt + 4);
      bits = le16(fmt + 14);
      if (format != 1 || bits != 16 || (channels != 1 && channels != 2)) {
        Serial.printf("[AudioOut] 지원 안 함: format=%u bits=%u ch=%u (PCM 16bit만)\n", format, bits, channels);
        return false;
      }
      if (!skipBytes(in, size - 16 + (size & 1))) return false;
    } else if (memcmp(ch, "data", 4) == 0) {
      dataSize = size;
      break;
    } else {
      if (!skipBytes(in, size + (size & 1))) return false;   // LIST 등 무시
    }
  }
  if (channels == 0) { Serial.println("[AudioOut] fmt 청크 없음"); return false; }

  if (sampleRate != REC_SAMPLE_RATE) i2s_set_sample_rates(SPK_PORT, sampleRate);
  Serial.printf("[AudioOut] 재생 %luHz %uch %lu bytes\n", (unsigned long)sampleRate, channels, (unsigned long)dataSize);

  // 3) 받으면서 재생 (dataSize가 0이나 0xFFFFFFFF면 연결이 끝날 때까지)
  bool unknownLen = (dataSize == 0 || dataSize == 0xFFFFFFFF);
  uint32_t remaining = dataSize;
  uint8_t inBuf[FRAMES * 2 * 2];
  bool ok = true;

  while (unknownLen || remaining > 0) {
    if (stopFlag && *stopFlag) { Serial.println("[AudioOut] 더블탭 -> 재생 중단"); break; }

    size_t frameBytes = channels * 2;
    size_t want = (size_t)FRAMES * frameBytes;
    if (!unknownLen) want = min(want, (size_t)remaining);
    want -= want % frameBytes;
    if (want == 0) break;

    if (!readExact(in, inBuf, want)) {
      if (!unknownLen) { Serial.println("[AudioOut] 수신 끊김"); ok = false; }
      break;   // 길이 미상이면 연결 종료 = 재생 끝
    }
    if (!unknownLen) remaining -= want;

    size_t frames = want / frameBytes;
    const int16_t* src = (const int16_t*)inBuf;
    for (size_t i = 0; i < frames; i++) {
      int16_t l = (int16_t)(src[i * channels] * AUDIO_PLAY_VOLUME);
      int16_t r = (channels == 2) ? (int16_t)(src[i * 2 + 1] * AUDIO_PLAY_VOLUME) : l;
      outBuf[2 * i] = l;
      outBuf[2 * i + 1] = r;
    }
    if (!writeFrames(frames)) { ok = false; break; }
  }

  i2s_zero_dma_buffer(SPK_PORT);
  if (sampleRate != REC_SAMPLE_RATE) i2s_set_sample_rates(SPK_PORT, REC_SAMPLE_RATE);
  return ok;
}
