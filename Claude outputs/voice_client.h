#ifndef VOICE_CLIENT_H
#define VOICE_CLIENT_H

#include <Arduino.h>

enum VoiceState {
  VOICE_IDLE,        // 대기
  VOICE_LISTENING,   // 녹음 중 (더블탭 = 녹음 종료)
  VOICE_PROCESSING,  // AI 응답 대기 (더블탭 무시)
  VOICE_PLAYING      // 응답 음성 재생 중 (더블탭 = 재생 중단)
};

bool voiceBegin(const char* deviceId);   // LittleFS·마이크·스피커·광센서·태스크 준비
void voiceOnDoubleTap();                 // 메인 루프: 더블탭 감지 시 호출
void voiceUpdate();                      // 메인 루프: 매 루프 호출 (표정·LED 반영)
bool voiceIsBusy();                      // 교신 중이면 true (터치 반응·슬립 억제용)

#endif
