// MicTest.ino — INMP441 단독 테스트 + 무음 감지(녹음 종료) 임계값 튜닝
// 배선: VDD 3.3V(5V 금지), GND, L/R=GND(왼쪽 채널), SCK 32, WS 13, SD 33
// 시리얼(115200, Newline):  r = 녹음 세션 시작(더블탭 대신),  c = 소음 기준 다시 측정

#include <driver/i2s.h>
#include <esp_idf_version.h>

#define MIC_PORT        I2S_NUM_0
#define MIC_SCK         32
#define MIC_WS          13     // 스피커 LRC(25)와 분리
#define MIC_SD          33
#define SAMPLE_RATE     16000
#define BLOCK_SAMPLES   256    // 16ms 단위
#define MIC_SHIFT       14     // 32bit -> 16bit 변환 시프트 (작을수록 소리 큼)

// 무음 감지 파라미터 (테스트하며 조정)
#define NOISE_CAL_MS        1000   // 시작 시 소음 측정 시간
#define SPEECH_FACTOR       3.0f   // 소음 RMS의 몇 배 이상이면 말소리
#define SPEECH_MIN_RMS      300.0f // 임계값 하한
#define WAIT_SPEECH_MS      3000   // 시작 후 이 시간 동안 말 없으면 '무응답'
#define SILENCE_END_MS      1200   // 말한 뒤 이만큼 조용하면 종료
#define MAX_RECORD_MS       8000   // 최대 녹음 길이 (RAM/전송 시간 고려)

static float dcOffset = 0;
static float noiseRms = 0;
static float speechThreshold = SPEECH_MIN_RMS;

static bool setupMic() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;   // INMP441은 24bit를 32bit 슬롯으로 출력
  cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;    // 값이 전부 0이면 ONLY_RIGHT로 바꿔 보기
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 4;
  cfg.dma_buf_len = BLOCK_SAMPLES;
  cfg.use_apll = false;

  i2s_pin_config_t pins = {};
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(4, 4, 0)
  pins.mck_io_num = I2S_PIN_NO_CHANGE;   // 0으로 두면 GPIO0에 MCLK가 출력됨
#endif
  pins.bck_io_num = MIC_SCK;
  pins.ws_io_num = MIC_WS;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = MIC_SD;

  if (i2s_driver_install(MIC_PORT, &cfg, 0, nullptr) != ESP_OK) return false;
  if (i2s_set_pin(MIC_PORT, &pins) != ESP_OK) { i2s_driver_uninstall(MIC_PORT); return false; }
  i2s_zero_dma_buffer(MIC_PORT);
  return true;
}

// 한 블록 읽어 RMS 반환. 실패 시 -1
static float readBlockRms() {
  static int32_t raw[BLOCK_SAMPLES];
  size_t bytesRead = 0;
  if (i2s_read(MIC_PORT, raw, sizeof(raw), &bytesRead, pdMS_TO_TICKS(100)) != ESP_OK || bytesRead == 0) {
    return -1;
  }
  int n = bytesRead / sizeof(int32_t);
  double sumSq = 0;
  for (int i = 0; i < n; i++) {
    float x = (float)(raw[i] >> MIC_SHIFT);
    dcOffset = dcOffset * 0.995f + x * 0.005f;   // DC 성분 제거
    float y = x - dcOffset;
    if (y > 32767) y = 32767; else if (y < -32768) y = -32768;
    sumSq += (double)y * y;
  }
  return sqrt(sumSq / n);
}

static void calibrateNoise() {
  Serial.println("[Mic] 소음 기준 측정 중... 1초간 조용히");
  unsigned long start = millis();
  double sum = 0; int cnt = 0;
  while (millis() - start < NOISE_CAL_MS) {
    float rms = readBlockRms();
    if (rms >= 0) { sum += rms; cnt++; }
  }
  if (cnt == 0) { Serial.println("[Mic] 읽기 실패 - 배선/채널 설정 확인"); return; }
  noiseRms = sum / cnt;
  speechThreshold = max(noiseRms * SPEECH_FACTOR, SPEECH_MIN_RMS);
  Serial.printf("[Mic] 소음 RMS %.0f -> 말소리 임계값 %.0f\n", noiseRms, speechThreshold);
}

// 더블탭 이후 동작을 흉내낸 녹음 세션 (실제 저장 없이 길이만 측정)
static void runRecordSession() {
  Serial.println("\n[Rec] 녹음 시작 (말해 보세요)");
  unsigned long start = millis(), lastVoice = 0;
  bool heardSpeech = false;

  while (true) {
    unsigned long now = millis();
    float rms = readBlockRms();
    if (rms < 0) { Serial.println("[Rec] 읽기 실패 -> 중단"); return; }

    if (rms >= speechThreshold) {
      if (!heardSpeech) Serial.printf("[Rec] 말소리 감지 (%.0f)\n", rms);
      heardSpeech = true;
      lastVoice = now;
    }

    if (!heardSpeech && now - start >= WAIT_SPEECH_MS) {
      Serial.println("[Rec] 무응답 -> 종료 (EXPR_LISTENING으로 다시 말해 달라고 할 상황)");
      return;
    }
    if (heardSpeech && now - lastVoice >= SILENCE_END_MS) {
      unsigned long dur = lastVoice - start + SILENCE_END_MS;
      Serial.printf("[Rec] 무음 감지 -> 종료. 길이 %.1f초, WAV 약 %lu KB\n",
                    dur / 1000.0f, (unsigned long)(dur * SAMPLE_RATE * 2 / 1000 / 1024));
      return;
    }
    if (now - start >= MAX_RECORD_MS) {
      Serial.println("[Rec] 최대 길이 도달 -> 종료");
      return;
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  if (!setupMic()) {
    Serial.println("[Mic] I2S 초기화 실패");
    while (true) delay(1000);
  }
  delay(200);   // 마이크 안정화
  calibrateNoise();
  Serial.println("[Mic] 'r' = 녹음 세션, 'c' = 소음 재측정. 평소엔 레벨 출력");
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'r') runRecordSession();
    else if (c == 'c') calibrateNoise();
  }

  // 레벨 미터 (200ms마다)
  static unsigned long lastPrint = 0;
  static float peak = 0;
  float rms = readBlockRms();
  if (rms > peak) peak = rms;
  if (millis() - lastPrint >= 200) {
    lastPrint = millis();
    int bars = min(40, (int)(peak / 100));
    Serial.printf("[Level] %5.0f ", peak);
    for (int i = 0; i < bars; i++) Serial.print('#');
    Serial.println(peak >= speechThreshold ? "  <- 말소리" : "");
    peak = 0;
  }
}
