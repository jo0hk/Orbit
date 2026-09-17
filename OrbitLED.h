#ifndef ORBIT_LED_H
#define ORBIT_LED_H

#include <Adafruit_NeoPixel.h>

class OrbitLED {
private:
  Adafruit_NeoPixel pixels;
  int _numPixels;

public:
  OrbitLED(int n, int pin);
  
  // 초기화 및 기본 색상 설정 함수
  void begin();
  void showColor(int r, int g, int b, int brightness);
  
  // 효과 함수
  void breathEffect(int r, int g, int b);
  void playFadeEffect(int r, int g, int b, int durationMs);
};

#endif