#include "OrbitLED.h"

OrbitLED::OrbitLED(int n, int pin) 
  : pixels(n, pin, NEO_GRB + NEO_KHZ800), _numPixels(n) {}

void OrbitLED::begin() {
  pixels.begin();
  pixels.show();
}

// 평상시 숨쉬기 효과, 밝기 30 고정
void OrbitLED::breathEffect(int r, int g, int b) {
  for (int i = 10; i < 30; i++) { 
    pixels.setBrightness(i);
    for(int j=0; j<_numPixels; j++) pixels.setPixelColor(j, pixels.Color(r, g, b));
    pixels.show();
    delay(50);
  }
  for (int i = 30; i > 10; i--) {
    pixels.setBrightness(i);
    for(int j=0; j<_numPixels; j++) pixels.setPixelColor(j, pixels.Color(r, g, b));
    pixels.show();
    delay(50);
  }
}

// 단계 변화 및 감정 페이드 효과, 최대 밝기 150 고정
void OrbitLED::playFadeEffect(int r, int g, int b, int durationMs) {
  unsigned long start = millis();
  while (millis() - start < (unsigned long)durationMs) {
    for (int i = 0; i <= 150; i++) { 
      pixels.setBrightness(i);
      for(int j=0; j<_numPixels; j++) pixels.setPixelColor(j, pixels.Color(r, g, b));
      pixels.show();
      delay(5);
    }
    for (int i = 150; i >= 0; i--) {
      pixels.setBrightness(i);
      for(int j=0; j<_numPixels; j++) pixels.setPixelColor(j, pixels.Color(r, g, b));
      pixels.show();
      delay(5);
    }
  }
}