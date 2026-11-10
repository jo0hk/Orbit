// LightTest.ino — CdS 조도센서 단독 테스트
// 배선: 3.3V ── CdS ── GPIO34 ── 10kΩ ── GND   (밝을수록 전압↑)
// Wi-Fi 사용 중에는 ADC2(GPIO 0,2,4,12~15,25~27)를 못 쓰므로 반드시 ADC1(32~39) 사용

#define LIGHT_PIN       34        // ADC1, 입력 전용 핀
#define R_FIXED_OHM     10000.0f  // 분압 저항 값 (실제 저항에 맞게)
#define SAMPLE_COUNT    16        // 평균 낼 측정 횟수

// lux 근사용 상수 (GL5528 계열 데이터시트 기준 추정값, 실측 보정 필요)
#define LDR_R_AT_10LUX  15000.0f  // 10 lux일 때 CdS 저항
#define LDR_GAMMA       0.7f

static int readMilliVoltsAvg() {
  uint32_t sum = 0;
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    sum += analogReadMilliVolts(LIGHT_PIN);
    delay(2);
  }
  return sum / SAMPLE_COUNT;
}

// 전압 -> CdS 저항 -> lux 근사. 계산 불가 구간은 -1
static int estimateLux(int mv, float* outR) {
  if (mv <= 10 || mv >= 3290) { *outR = -1; return -1; }   // 0 나누기·포화 방지
  float r = R_FIXED_OHM * (3300.0f / mv - 1.0f);
  *outR = r;
  return (int)(10.0f * powf(LDR_R_AT_10LUX / r, 1.0f / LDR_GAMMA));
}

void setup() {
  Serial.begin(115200);
  delay(300);
  analogReadResolution(12);
  analogSetPinAttenuation(LIGHT_PIN, ADC_11db);   // 0~약 3.1V 측정
  Serial.println("[LightTest] 시작 - 손으로 가렸다 뗐다 해 보세요");
}

void loop() {
  int mv = readMilliVoltsAvg();
  float r;
  int lux = estimateLux(mv, &r);

  if (lux < 0) {
    Serial.printf("[Light] %4d mV | 범위 밖 (배선/저항 확인)\n", mv);
  } else {
    Serial.printf("[Light] %4d mV | CdS %7.0f Ω | 약 %5d lux %s\n",
                  mv, r, lux, (lux <= 50) ? "(어두움: AI 환기 권유 기준 50 이하)" : "");
  }
  delay(500);
}
