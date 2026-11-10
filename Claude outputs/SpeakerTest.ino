// SpeakerTest.ino — MAX98357A + 스피커 단독 테스트
// 배선: VIN 5V(또는 배터리 직결 2.5~5.5V), GND, LRC 25, BCLK 26, DIN 27, SD/GAIN 미연결
// 시리얼(115200, Newline):  1 = 440Hz 1초,  2 = 주파수 스윕,  3 = 띵동,  + / - = 볼륨

#include <driver/i2s.h>
#include <esp_idf_version.h>

#define SPK_PORT      I2S_NUM_1   // 마이크(I2S_NUM_0)와 다른 포트
#define SPK_BCLK      26
#define SPK_LRC       25
#define SPK_DIN       27
#define SAMPLE_RATE   16000       // AI 응답 wav와 같은 16kHz 모노 기준
#define FRAMES        256

static float volume = 0.3f;       // 0.0~1.0 (처음엔 작게)

static bool setupSpeaker() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;   // 양쪽에 같은 값 -> MAX98357A가 (L+R)/2 출력
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 6;
  cfg.dma_buf_len = FRAMES;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = true;   // 데이터가 끊기면 0을 출력 (잡음 방지)

  i2s_pin_config_t pins = {};
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(4, 4, 0)
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
#endif
  pins.bck_io_num = SPK_BCLK;
  pins.ws_io_num = SPK_LRC;
  pins.data_out_num = SPK_DIN;
  pins.data_in_num = I2S_PIN_NO_CHANGE;

  if (i2s_driver_install(SPK_PORT, &cfg, 0, nullptr) != ESP_OK) return false;
  if (i2s_set_pin(SPK_PORT, &pins) != ESP_OK) { i2s_driver_uninstall(SPK_PORT); return false; }
  i2s_zero_dma_buffer(SPK_PORT);
  return true;
}

// 사인파 재생. freqEnd != freqStart 이면 선형 스윕
static void playTone(float freqStart, float freqEnd, uint32_t ms) {
  static int16_t buf[FRAMES * 2];
  uint32_t total = (uint32_t)SAMPLE_RATE * ms / 1000;
  uint32_t done = 0;
  float phase = 0;

  while (done < total) {
    uint32_t n = min((uint32_t)FRAMES, total - done);
    for (uint32_t i = 0; i < n; i++) {
      float t = (float)(done + i) / total;
      float freq = freqStart + (freqEnd - freqStart) * t;
      // 앞뒤 10ms 페이드로 '틱' 소리 방지
      float env = 1.0f;
      uint32_t pos = done + i, fade = SAMPLE_RATE / 100;
      if (pos < fade) env = (float)pos / fade;
      else if (total - pos < fade) env = (float)(total - pos) / fade;

      int16_t s = (int16_t)(sinf(phase) * 32767.0f * volume * env);
      buf[2 * i] = s;
      buf[2 * i + 1] = s;
      phase += 2.0f * PI * freq / SAMPLE_RATE;
      if (phase > 2.0f * PI) phase -= 2.0f * PI;
    }
    size_t written = 0;
    if (i2s_write(SPK_PORT, buf, n * 2 * sizeof(int16_t), &written, pdMS_TO_TICKS(500)) != ESP_OK) {
      Serial.println("[Spk] i2s_write 실패");
      break;
    }
    done += n;
  }
  i2s_zero_dma_buffer(SPK_PORT);   // 재생 후 무음
}

void setup() {
  Serial.begin(115200);
  delay(300);
  if (!setupSpeaker()) {
    Serial.println("[Spk] I2S 초기화 실패");
    while (true) delay(1000);
  }
  Serial.println("[Spk] 1=440Hz, 2=스윕, 3=띵동, +/-=볼륨");
  playTone(880, 880, 150);   // 부팅 확인음
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();
  switch (c) {
    case '1': Serial.println("[Spk] 440Hz 1초"); playTone(440, 440, 1000); break;
    case '2': Serial.println("[Spk] 200 -> 4000Hz 스윕"); playTone(200, 4000, 3000); break;
    case '3': Serial.println("[Spk] 띵동"); playTone(1047, 1047, 250); playTone(784, 784, 400); break;
    case '+': volume = min(1.0f, volume + 0.1f); Serial.printf("[Spk] 볼륨 %.1f\n", volume); break;
    case '-': volume = max(0.0f, volume - 0.1f); Serial.printf("[Spk] 볼륨 %.1f\n", volume); break;
    default: break;
  }
}
