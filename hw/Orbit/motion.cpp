#include "motion.h"
#include <Wire.h>

const int MPU_I2C_ADDR = 0x68;

// 흔들기 감지 상수
static int shakeDirectionFlips = 0;
static unsigned long lastShakeActionTime = 0;
const unsigned long SHAKE_WINDOW = 1000;

// 만보기 임계치
const float STEP_PEAK_THRESHOLD = 1.05;
const float STEP_VALLEY_THRESHOLD = 0.85;
const unsigned long MIN_STEP_INTERVAL = 180;

enum StepState { WAITING_FOR_PEAK, WAITING_FOR_VALLEY };
static StepState stepState = WAITING_FOR_PEAK;
static unsigned long lastStepTime = 0;
static unsigned long peakTime = 0;

// 딥슬립 간 걸음 수 유지를 위한 RTC 변수
RTC_DATA_ATTR static int totalStepCount = 0;

// 센서 영점 보정 계수
static float accelScaleOffset = 1.0; 

static void initMPUSettings() {
  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x6B); Wire.write(0); // Power On
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1C); Wire.write(0x08); // 가속도 ±4g
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1B); Wire.write(0x08); // 자이로 ±500 deg/s
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1A); Wire.write(0x04); // DLPF 필터
  Wire.endTransmission();
}

void setupMotion() {
  Wire.begin(21, 22);
  Wire.setClock(100000);
  Wire.setTimeOut(25);
  initMPUSettings();

  // 부팅 직후 정지 상태 중력(1.0g) 캘리브레이션
  delay(100);
  float sumMag = 0;
  int samples = 0;

  for (int i = 0; i < 20; i++) {
    Wire.beginTransmission(MPU_I2C_ADDR);
    Wire.write(0x3B);
    if (Wire.endTransmission(false) == 0 && Wire.requestFrom((uint16_t)MPU_I2C_ADDR, (uint8_t)6, (bool)true) >= 6) {
      int16_t rawAx = Wire.read() << 8 | Wire.read();
      int16_t rawAy = Wire.read() << 8 | Wire.read();
      int16_t rawAz = Wire.read() << 8 | Wire.read();
      float ax = rawAx / 8192.0;
      float ay = rawAy / 8192.0;
      float az = rawAz / 8192.0;
      sumMag += sqrt(ax * ax + ay * ay + az * az);
      samples++;
    }
    delay(10);
  }

  if (samples > 0) {
    float avgMag = sumMag / samples;
    if (avgMag > 0.5) {
      accelScaleOffset = 1.0 / avgMag;
      Serial.printf("[Motion] 센서 오프셋 보정 완료 (측정: %.2fg, 계수: %.2f)\n", avgMag, accelScaleOffset);
    }
  }
}

MotionResult updateMotion() {
  MotionResult res = { false, false, totalStepCount };

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x3B);
  byte err = Wire.endTransmission(false);

  if (err != 0) {
    Wire.begin(21, 22);
    initMPUSettings();
    return res;
  }

  if (Wire.requestFrom((uint16_t)MPU_I2C_ADDR, (uint8_t)14, (bool)true) >= 14) {
    int16_t rawAx = Wire.read() << 8 | Wire.read();
    int16_t rawAy = Wire.read() << 8 | Wire.read();
    int16_t rawAz = Wire.read() << 8 | Wire.read();
    Wire.read(); Wire.read();
    int16_t rawGx = Wire.read() << 8 | Wire.read();
    int16_t rawGy = Wire.read() << 8 | Wire.read();
    int16_t rawGz = Wire.read() << 8 | Wire.read();

    float ax = (rawAx / 8192.0) * accelScaleOffset;
    float ay = (rawAy / 8192.0) * accelScaleOffset;
    float az = (rawAz / 8192.0) * accelScaleOffset;

    float gx = rawGx / 65.5;
    float gy = rawGy / 65.5;
    float gz = rawGz / 65.5;

    float mag = sqrt(ax * ax + ay * ay + az * az);

    if (mag < 0.05) {
      initMPUSettings();
      return res;
    }

    unsigned long now = millis();
    float totalGyroSpeed = sqrt(gx * gx + gy * gy + gz * gz);

    // 디버그용 주기적 센서 출력 주석 처리
    /*
    static unsigned long lastDebugPrint = 0;
    if (now - lastDebugPrint > 200) {
      lastDebugPrint = now;
      Serial.printf("센서 가속도(mag): %.2f g | 자이로 회전: %.2f\n", mag, totalGyroSpeed);
    }
    */
    
    // 1초 이상 미감지 시 흔들기 카운터 리셋
    if (now - lastShakeActionTime > SHAKE_WINDOW && shakeDirectionFlips > 0) {
      shakeDirectionFlips = 0;
    }

    // 1. 흔들기 감지
    if (mag > 1.8 && totalGyroSpeed > 130.0) {
      if (now - lastShakeActionTime > 120) {
        shakeDirectionFlips++;
        lastShakeActionTime = now;
      }
    }

    if (shakeDirectionFlips >= 2) {
      res.isShaken = true;
      shakeDirectionFlips = 0;
    }

    // 2. 걸음 수 감지
    switch (stepState) {
      case WAITING_FOR_PEAK:
        if (mag > STEP_PEAK_THRESHOLD && (now - lastStepTime > MIN_STEP_INTERVAL)) {
          stepState = WAITING_FOR_VALLEY;
          peakTime = now;
        }
        break;

      case WAITING_FOR_VALLEY:
        if (mag < STEP_VALLEY_THRESHOLD) {
          totalStepCount++;
          lastStepTime = now;
          stepState = WAITING_FOR_PEAK;
          res.stepDetected = true;
          res.currentSteps = totalStepCount;
        } else if (now - peakTime > 900) {
          stepState = WAITING_FOR_PEAK;
        }
        break;
    }
  }

  return res;
}

void resetSteps() {
  totalStepCount = 0;
}