#ifndef AUDIO_IN_H
#define AUDIO_IN_H

#include <Arduino.h>

enum RecordResult {
  REC_OK,          // 녹음 완료 (파일 저장됨)
  REC_NO_SPEECH,   // 말이 없었음 / 말하기 전에 취소 (파일 삭제됨)
  REC_ERROR        // 마이크·파일 오류 (파일 삭제됨)
};

bool audioInBegin();   // INMP441 I2S 초기화 (I2S_NUM_0)

// path에 16kHz 16bit 모노 WAV로 녹음.
// *stopFlag가 true가 되면 즉시 종료(더블탭), 아니면 무음 감지·최대 길이로 종료
RecordResult audioInRecord(const char* path, volatile bool* stopFlag, uint32_t* outFileBytes);

#endif
