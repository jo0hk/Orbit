#include "motion.h"
#include <Wire.h>

const int MPU_I2C_ADDR = 0x68;

// 흔들기 변수
static int shakeDirectionFlips = 0;
static unsigned long lastShakeActionTime = 0;
const unsigned long SHAKE_WINDOW = 1000;

// 만보기 변수
const float STEP_PEAK_THRESHOLD = 1.05;
const float STEP_VALLEY_THRESHOLD = 0.85;
const unsigned long MIN_STEP_INTERVAL = 180;

enum StepState { WAITING_FOR_PEAK, WAITING_FOR_VALLEY };
static StepState stepState = WAITING_FOR_PEAK;
static unsigned long lastStepTime = 0;
static unsigned long peakTime = 0;
RTC_DATA_ATTR static int totalStepCount = 0;

// ★ 센서 캘리브레이션 오프셋 변수
static float accelScaleOffset = 1.0; 

static void initMPUSettings() {
  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x6B); Wire.write(0);
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1C); Wire.write(0x08); // ±4g
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1B); Wire.write(0x08); // ±500 deg/s
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1A); Wire.write(0x04);
  Wire.endTransmission();
}

void setupMotion() {
  Wire.begin(21, 22);
  Wire.setClock(100000);
  Wire.setTimeOut(25);
  initMPUSettings();

  // ★ [핵심] 부팅 직후 20번 센서값을 읽어 정지 상태 중력을 1.0g로 강제 보정
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
      accelScaleOffset = 1.0 / avgMag; // 정지 시 가속도를 정확히 1.0g로 만드는 계수 산출
      Serial.printf("[Motion] 센서 오프셋 보정 완료! (측정 평균: %.2fg -> 보정 계수: %.2f)\n", avgMag, accelScaleOffset);
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

    // ★ 오프셋 보정 계수(accelScaleOffset) 적용
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

    static unsigned long lastDebugPrint = 0;
    if (now - lastDebugPrint > 200) {
      lastDebugPrint = now;
      Serial.print("센서 가속도(mag): ");
      Serial.print(mag);
      Serial.print(" g | 자이로 회전: ");
      Serial.println(totalGyroSpeed);
    }
    
    // 1초 이상 지났으면 리셋
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

    // 2. 걸음수 감지
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