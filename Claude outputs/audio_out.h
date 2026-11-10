#ifndef AUDIO_OUT_H
#define AUDIO_OUT_H

#include <Arduino.h>
#include <WiFi.h>
#include "config.h"

bool audioOutBegin();   // MAX98357A I2S 초기화 (I2S_NUM_1). 대기 중엔 무음 출력

// 효과음 (블로킹, 음성 태스크에서만 호출)
void audioOutTone(float freq, uint32_t ms, float volume = AUDIO_TONE_VOLUME);

// WAV(PCM 16bit 모노/스테레오) 스트림을 받으면서 재생. *stopFlag가 true면 중단
bool audioOutPlayWav(WiFiClient& in, volatile bool* stopFlag);

#endif
