#include "motion.h"
#include <Wire.h>

const int MPU_I2C_ADDR = 0x68;

// 흔들기 관련 변수
static float prevAx = 0, prevAy = 0, prevAz = 0;
static int shakeDirectionFlips = 0;
static int lastDirection = 0;
static unsigned long lastShakeActionTime = 0;
const unsigned long SHAKE_WINDOW = 1000;

// 만보기 관련 변수
const float STEP_PEAK_THRESHOLD = 1.15;
const float STEP_VALLEY_THRESHOLD = 0.95;
const unsigned long MIN_STEP_INTERVAL = 200;

enum StepState { WAITING_FOR_PEAK, WAITING_FOR_VALLEY };
static StepState stepState = WAITING_FOR_PEAK;
static unsigned long lastStepTime = 0;
static unsigned long peakTime = 0;
static int totalStepCount = 0;

static void initMPUSettings() {
  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1C);
  Wire.write(0x08);
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1B);
  Wire.write(0x08);
  Wire.endTransmission();

  Wire.beginTransmission(MPU_I2C_ADDR);
  Wire.write(0x1A);
  Wire.write(0x04);
  Wire.endTransmission();
}

void setupMotion() {
  Wire.begin(21, 22);
  Wire.setClock(100000);
  Wire.setTimeOut(25);
  initMPUSettings();
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

    float ax = rawAx / 8192.0;
    float ay = rawAy / 8192.0;
    float az = rawAz / 8192.0;

    float gx = rawGx / 65.5;
    float gy = rawGy / 65.5;
    float gz = rawGz / 65.5;

    float mag = sqrt(ax * ax + ay * ay + az * az);

    if (mag < 0.05) {
      initMPUSettings();
      return res;
    }

    unsigned long now = millis();

    // 1. 흔들기 감지
    float totalGyroSpeed = sqrt(gx * gx + gy * gy + gz * gz);

    static unsigned long lastDebugPrint = 0;
    if (now - lastDebugPrint > 500) {
      lastDebugPrint = now;
      Serial.print("센서 가속도(mag): ");
      Serial.print(mag);
      Serial.print(" g | 자이로 회전: ");
      Serial.println(totalGyroSpeed);
    }
    
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

    if (now - lastShakeActionTime > SHAKE_WINDOW && shakeDirectionFlips > 0) {
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
        } else if (now - peakTime > 500) {
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