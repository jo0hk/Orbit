#include "audio_in.h"
#include "config.h"
#include <driver/i2s.h>
#include <esp_idf_version.h>
#include <LittleFS.h>

#define MIC_PORT        I2S_NUM_0
#define BLOCK_SAMPLES   256      // 16ms

static bool micReady = false;
static int32_t rawBuf[BLOCK_SAMPLES];
static int16_t pcmBuf[BLOCK_SAMPLES];
static float dcOffset = 0;

bool audioInBegin() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate = REC_SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;   // INMP441: 24bit를 32bit 슬롯으로 출력
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;    // MicTest와 동일
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8;          // 128ms 버퍼: 플래시 쓰기 지연 동안 샘플 유실 방지
  cfg.dma_buf_len = BLOCK_SAMPLES;
  cfg.use_apll = false;

  i2s_pin_config_t pins = {};
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(4, 4, 0)
  pins.mck_io_num = I2S_PIN_NO_CHANGE;   // 0이면 GPIO0에 MCLK 출력됨
#endif
  pins.bck_io_num = MIC_SCK_PIN;
  pins.ws_io_num = MIC_WS_PIN;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = MIC_SD_PIN;

  if (i2s_driver_install(MIC_PORT, &cfg, 0, nullptr) != ESP_OK) {
    Serial.println("[AudioIn] I2S 설치 실패");
    return false;
  }
  if (i2s_set_pin(MIC_PORT, &pins) != ESP_OK) {
    Serial.println("[AudioIn] I2S 핀 설정 실패");
    i2s_driver_uninstall(MIC_PORT);
    return false;
  }
  micReady = true;
  return true;
}

// 한 블록 읽어 16bit PCM(pcmBuf)으로 변환하고 RMS 반환. 실패 시 -1
static float readBlock(int* outCount) {
  size_t bytesRead = 0;
  if (i2s_read(MIC_PORT, rawBuf, sizeof(rawBuf), &bytesRead, pdMS_TO_TICKS(100)) != ESP_OK || bytesRead == 0) {
    return -1;
  }
  int n = bytesRead / sizeof(int32_t);
  double sumSq = 0;
  for (int i = 0; i < n; i++) {
    float x = (float)(rawBuf[i] >> REC_MIC_SHIFT);
    dcOffset = dcOffset * 0.995f + x * 0.005f;   // DC 성분 제거
    float y = x - dcOffset;
    if (y > 32767.0f) y = 32767.0f; else if (y < -32768.0f) y = -32768.0f;
    pcmBuf[i] = (int16_t)y;
    sumSq += (double)y * y;
  }
  *outCount = n;
  return sqrt(sumSq / n);
}

static void put16(uint8_t* p, uint16_t v) { p[0] = v & 0xFF; p[1] = v >> 8; }
static void put32(uint8_t* p, uint32_t v) { for (int i = 0; i < 4; i++) p[i] = (v >> (8 * i)) & 0xFF; }

static void writeWavHeader(File& f, uint32_t dataBytes) {
  uint8_t h[44];
  memcpy(h, "RIFF", 4);      put32(h + 4, 36 + dataBytes);
  memcpy(h + 8, "WAVEfmt ", 8);
  put32(h + 16, 16);         // fmt 청크 크기
  put16(h + 20, 1);          // PCM
  put16(h + 22, 1);          // 모노
  put32(h + 24, REC_SAMPLE_RATE);
  put32(h + 28, REC_SAMPLE_RATE * 2);   // byte rate
  put16(h + 32, 2);          // block align
  put16(h + 34, 16);         // bits
  memcpy(h + 36, "data", 4); put32(h + 40, dataBytes);
  f.write(h, sizeof(h));
}

RecordResult audioInRecord(const char* path, volatile bool* stopFlag, uint32_t* outFileBytes) {
  *outFileBytes = 0;
  if (!micReady) return REC_ERROR;

  // 0) 시작음 잔향 버리기
  int n = 0;
  unsigned long ts = millis();
  while (millis() - ts < REC_SETTLE_MS) readBlock(&n);
  
  // 1) 소음 측정
  int cnt = 0;
  double sum = 0;
  unsigned long t0 = millis();
  while (millis() - t0 < REC_NOISE_CAL_MS) {
    float r = readBlock(&n);
    if (r >= 0) { sum += r; cnt++; }
  }
  if (cnt == 0) {
    Serial.println("[AudioIn] 마이크 읽기 실패");
    return REC_ERROR;
  }
  float noise = sum / cnt;
  float startTh = max(noise * REC_SPEECH_FACTOR, REC_SPEECH_MIN_RMS);
  float keepTh = startTh * 0.5f;   // 말하는 도중엔 낮은 기준 (작은 음절에 끊기지 않게)
  Serial.printf("[AudioIn] 소음 %.0f -> 시작 %.0f / 유지 %.0f\n", noise, startTh, keepTh);

  // 2) 녹음 (헤더는 자리만 잡고 끝에서 길이 기록)
  File f = LittleFS.open(path, "w");
  if (!f) {
    Serial.println("[AudioIn] 파일 열기 실패");
    return REC_ERROR;
  }
  writeWavHeader(f, 0);

  uint32_t dataBytes = 0;
  unsigned long start = millis(), lastVoice = 0;
  bool heard = false;
  uint32_t loudMs = 0;
  RecordResult result = REC_OK;

  while (true) {
    float rms = readBlock(&n);
    if (rms < 0) { Serial.println("[AudioIn] 읽기 실패"); result = REC_ERROR; break; }

    size_t len = (size_t)n * sizeof(int16_t);
    if (f.write((uint8_t*)pcmBuf, len) != len) {
      Serial.println("[AudioIn] 저장 실패 (용량 부족?)");
      result = REC_ERROR;
      break;
    }
    dataBytes += len;

    unsigned long now = millis();
    if (!heard) {
      // 짧은 소리(탭·충격음)는 무시: 기준을 넘는 소리가 REC_SPEECH_MIN_MS 이상 이어져야 인정
      if (rms >= startTh) {
        loudMs += (uint32_t)n * 1000 / REC_SAMPLE_RATE;
        if (loudMs >= REC_SPEECH_MIN_MS) {
          heard = true;
          lastVoice = now;
          Serial.printf("[AudioIn] 말소리 감지 (%.0f, %lums 지속)\n", rms, (unsigned long)loudMs);
        }
      } else {
        loudMs = 0;
      }
    } else if (rms >= keepTh) {
      lastVoice = now;
    }

    if (stopFlag && *stopFlag) {
      Serial.println("[AudioIn] 더블탭 -> 종료");
      result = heard ? REC_OK : REC_NO_SPEECH;
      break;
    }
    if (!heard && now - start >= REC_WAIT_SPEECH_MS) { result = REC_NO_SPEECH; break; }
    if (heard && now - lastVoice >= REC_SILENCE_END_MS) { Serial.println("[AudioIn] 무음 -> 자동 종료"); break; }
    if (now - start >= REC_MAX_MS) { Serial.println("[AudioIn] 최대 길이 -> 종료"); break; }
  }

  // 3) 헤더에 실제 길이 기록
  f.seek(0);
  writeWavHeader(f, dataBytes);
  f.close();

  if (result != REC_OK) {
    LittleFS.remove(path);
    return result;
  }
  *outFileBytes = dataBytes + 44;
  Serial.printf("[AudioIn] 녹음 완료 %.1f초 (%lu bytes)\n",
                dataBytes / (REC_SAMPLE_RATE * 2.0f), (unsigned long)*outFileBytes);
  return REC_OK;
}
