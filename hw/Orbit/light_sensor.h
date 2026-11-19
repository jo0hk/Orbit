#ifndef LIGHT_SENSOR_H
#define LIGHT_SENSOR_H

void lightBegin();
// 조도(lux) 근사값 0~1000. ADC 설정·읽기 실패 시에만 -1
// CdS 특성값은 추정치라 실제 lux와 차이가 있음 (AI 판단 기준: 50 이하 = 어두움)
int lightReadLux();

#endif
