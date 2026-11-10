#ifndef LIGHT_SENSOR_H
#define LIGHT_SENSOR_H

void lightBegin();
// 조도(lux) 근사값. 측정 불가(배선 이상·포화)면 -1
// CdS 특성값은 추정치라 실제 lux와 차이가 있음 (AI 판단 기준: 50 이하 = 어두움)
int lightReadLux();

#endif
