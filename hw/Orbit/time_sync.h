#ifndef TIME_SYNC_H
#define TIME_SYNC_H

void setupTimeSync();         // setup()에서 1회 (Wi-Fi 연결 전이어도 됨)
void updateDailyStepReset();  // loop()에서 호출, 내부적으로 1초 간격

#endif