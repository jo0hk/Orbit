#include "OrbitFace.h"
#include <math.h>
#include <string.h>

// ===== 조정용 상수 =====
// OLED 1장 전송 동안 loop가 멈추므로, 실측값("[Face] 5초 통계" 로그)을 보고 조정
static const uint16_t FRAME_MS         = 40;    // 전환/행동 중 최소 프레임 간격
static const float    MORPH_K          = 0.3f;  // 목표 모양으로 다가가는 비율 (프레임당)
static const float    FAST_K           = 0.6f;  // 깜빡임 등 빠른 변화
static const float    REDRAW_DIFF      = 0.3f;  // 이만큼(px) 이상 바뀌면 다시 그림

static const uint16_t HAPPY_BOUNCE_MS  = 150;   // 표정별 대기 애니메이션 간격
static const uint16_t SAD_TEAR_MS      = 150;
static const uint16_t ANGRY_SHAKE_MS   = 120;
static const uint16_t CALM_BREATH_MS   = 600;
static const uint16_t LISTEN_PULSE_MS  = 150;
static const uint16_t THINK_DOTS_MS    = 400;
static const uint16_t DIZZY_FRAME_MS   = 120;
static const uint16_t SLEEP_FRAME_MS   = 300;

#define FACE_STATS_ENABLED 0                    // 1이면 5초마다 전송 시간/loop 지연 로그
static const uint16_t STATS_PERIOD_MS  = 5000;

// ===== 좌표 기준 =====
static const int XC = 64;          // x_center
static const int YC = 28;          // y_center
static const int ES = 24;          // eye_spacing
static const int MY = YC + 18;     // mouth_y
static const int LID_NONE = 99;    // 눈꺼풀 가림 없음

// 대기 애니메이션 값 (모양 변형과 별개로, 정해진 간격마다 계단식으로 바뀜)
enum { ID_DX, ID_DY, ID_RY, ID_LID, ID_TEAR, ID_DOTS };

// ===== FaceShape 계산 도우미 =====
static_assert(sizeof(FaceShape) % sizeof(float) == 0, "FaceShape must contain only floats");
static const int SHAPE_N = sizeof(FaceShape) / sizeof(float);

static float maxDiff(const FaceShape& a, const FaceShape& b) {
  const float* pa = (const float*)&a;
  const float* pb = (const float*)&b;
  float m = 0;
  for (int i = 0; i < SHAPE_N; i++) m = fmaxf(m, fabsf(pa[i] - pb[i]));
  return m;
}

static void lerpShape(FaceShape& a, const FaceShape& b, float k) {
  float* pa = (float*)&a;
  const float* pb = (const float*)&b;
  for (int i = 0; i < SHAPE_N; i++) pa[i] += (pb[i] - pa[i]) * k;
}

static inline int rnd(float v) { return (int)lroundf(v); }

static void setTri(EyeShape& e, float a, float b, float c, float d, float f, float g) {
  e.tri[0] = a; e.tri[1] = b; e.tri[2] = c; e.tri[3] = d; e.tri[4] = f; e.tri[5] = g;
}

// s = -1(왼눈) / +1(오른눈). 기본 NORMAL 눈. 안 쓰는 자르기 도형은 눈 바로 바깥에 대기시켜서
// 다른 표정으로 바뀔 때 그 자리에서 미끄러져 들어오게 함
static void defaultEye(EyeShape& e, int s) {
  e.cx = 0; e.cy = 0; e.rx = 8; e.ry = 12;
  setTri(e, -11, -16, 11, -16, 11 * s, -16);       // 눈 위 (안 보임)
  e.hol[0] = 0; e.hol[1] = 20; e.hol[2] = 6; e.hol[3] = 7;   // 눈 아래 (안 보임)
  e.cutBot = 14;
  e.cutTop = -14;
  e.lid = 0;
  e.brow[0] = 10 * s; e.brow[1] = -14; e.brow[2] = -9 * s; e.brow[3] = -7; e.brow[4] = 0;  // 두께 0 = 안 보임
}

// ----- 입 모양 (u = -1 왼쪽 끝 ~ +1 오른쪽 끝, 값 = mouth_y 기준 높이) -----
static float mVTop(float u)     { return -3 * fabsf(u); }                 // V자 미소
static float mThinkTop(float)   { return -2; }
static float mThinkBot(float)   { return -1; }
static float mSadTop(float u)   { return -2 + 3 * fabsf(u); }             // 굵은 역V
static float mSadBot(float u)   { return -1 + 3 * fabsf(u); }
static float mAngryTop(float)   { return -1; }
static float mAngryBot(float)   { return 0; }
static float mHappyTop(float)   { return -1; }
static float mHappyBot(float u) {                                         // 아래 반원
  float k = u * 7.0f / 7.5f;
  return -1 + 5.5f * sqrtf(fmaxf(0, 1 - k * k)) - 0.49f;
}
static float mCalmTop(float u)  { return 1 - 3 * fabsf(u); }              // 작은 미소
static float mBigTop(float u)   { return 1 - 4 * fabsf(u); }              // 활짝 미소
static float mBigBot(float u)   { return mBigTop(u) + 2 * sqrtf(fmaxf(0, 1 - u * u)); }
static float mOTop(float u)     { return -1 - 2.5f * sqrtf(fmaxf(0, 1 - u * u)); }  // '오?'
static float mOBot(float u)     { return -1 + 2.5f * sqrtf(fmaxf(0, 1 - u * u)); }
static float mFlat(float)       { return -1; }                            // 무표정
static float mSmirk(float u)    { return -1.5f * u - 1 + (u < 0 ? 0 : -1.5f * u); }  // 씩

static void setMouth(FaceShape& f, float w, float (*top)(float), float (*bot)(float)) {
  f.w = w;
  for (int i = 0; i < MOUTH_PTS; i++) {
    float u = -1.0f + 2.0f * i / (MOUTH_PTS - 1);
    f.top[i] = top(u);
    f.bot[i] = bot(u);
  }
}

// ===== 표정 정의 =====
void OrbitFace::baseShape(FaceExpression e, FaceShape& f) {
  defaultEye(f.L, -1);
  defaultEye(f.R, 1);
  f.mx = 0; f.my = 0;
  setMouth(f, 8, mVTop, mVTop);
  f.cheek = 0; f.tear = 0; f.dots = 0;

  switch (e) {
    case EXPR_LISTENING:   // 가로로 긴 타원 눈 + V자 미소
      f.L.rx = f.R.rx = 12;
      f.L.ry = f.R.ry = 5;
      break;

    case EXPR_THINKING:    // 위를 보는 눈(아랫부분 평평) + 작은 일자 입 + 말줄임표
      f.L.cx = f.R.cx = 2;
      f.L.cy = f.R.cy = -2;
      f.L.cutBot = f.R.cutBot = 4;
      setMouth(f, 3, mThinkTop, mThinkBot);
      f.dots = 1;
      break;

    case EXPR_SAD:         // 바깥쪽 위를 잘라낸 처진 눈 + 눈물 + 굵은 역V 입
      f.L.cy = f.R.cy = 2;
      f.L.rx = f.R.rx = 9;
      f.L.ry = f.R.ry = 9;
      setTri(f.L, -11, -9, 11, -9, -11, 1);
      setTri(f.R, -11, -9, 11, -9, 11, 1);
      setMouth(f, 7, mSadTop, mSadBot);
      f.tear = 1;
      break;

    case EXPR_ANGRY:       // 안쪽 위를 잘라낸 노려보는 눈 + 3px 눈썹 + 일자 입
      f.L.cy = f.R.cy = 2;
      f.L.rx = f.R.rx = 9;
      f.L.ry = f.R.ry = 9;
      setTri(f.L, -11, -8, 11, -8, 11, 1);
      setTri(f.R, -11, -8, 11, -8, -11, 1);
      f.L.brow[4] = f.R.brow[4] = 3;
      setMouth(f, 7, mAngryTop, mAngryBot);
      break;

    case EXPR_HAPPY:       // 두꺼운 반달 눈 + 볼터치 + 활짝 벌린 입
      f.L.cy = f.R.cy = 2;
      f.L.rx = f.R.rx = 9;
      f.L.ry = f.R.ry = 8;
      f.L.hol[1] = f.R.hol[1] = 5;
      f.L.cutBot = f.R.cutBot = 3;
      setMouth(f, 7, mHappyTop, mHappyBot);
      f.cheek = 1;
      break;

    case EXPR_CALM:        // 반쯤 감은 눈 + 눈꺼풀 선 + 볼터치 + 작은 미소
      f.L.cy = f.R.cy = 1;
      f.L.rx = f.R.rx = 9;
      f.L.ry = f.R.ry = 7;
      f.L.cutTop = f.R.cutTop = 0;
      f.L.lid = f.R.lid = 1;
      setMouth(f, 6, mCalmTop, mCalmTop);
      f.cheek = 1;
      break;

    default:               // NORMAL (BLINK/DIZZY/SLEEP의 바탕도 NORMAL)
      break;
  }
}

void OrbitFace::closedShape(FaceShape& f) {   // 감은 눈 (납작한 타원)
  baseShape(EXPR_NORMAL, f);
  f.L.ry = f.R.ry = 1;
}

// ===== NORMAL 랜덤 행동 =====
enum {
  ACT_LOOK_RIGHT, ACT_LOOK_LEFT, ACT_LOOK_UP_LEFT, ACT_LOOK_UP_RIGHT, ACT_LOOK_RIGHT_O,
  ACT_TILT_SMILE, ACT_SQUINT_SMILE, ACT_LOOK_DOWN_SMIRK, ACT_DOUBLE_BLINK, ACT_COUNT
};

static void look(FaceShape& f, float dx, float dy) {
  EyeShape* eyes[2] = { &f.L, &f.R };
  for (EyeShape* e : eyes) { e->cx += dx; e->cy += dy; e->cutBot += dy; }
  f.mx += dx / 4; f.my += dy / 3;
}

void OrbitFace::applyAction(int8_t a, FaceShape& f) {
  switch (a) {
    case ACT_LOOK_RIGHT:      look(f, 4, 0); break;
    case ACT_LOOK_LEFT:       look(f, -4, 0); break;
    case ACT_LOOK_UP_LEFT:    look(f, -4, -2); setMouth(f, 5, mFlat, mFlat); break;
    case ACT_LOOK_UP_RIGHT:   look(f, 4, -2); break;
    case ACT_LOOK_RIGHT_O:    look(f, 4, 0); setMouth(f, 4, mOTop, mOBot); break;
    case ACT_TILT_SMILE:      // 고개 갸웃 + 활짝 미소
      f.L.cy -= 2; f.R.cy += 2; f.R.cutBot += 2; f.mx += 1;
      setMouth(f, 9, mBigTop, mBigBot);
      break;
    case ACT_SQUINT_SMILE:    // 눈웃음: 눈 아래를 둥글게 파냄
      f.L.hol[1] = f.R.hol[1] = 12; f.L.hol[2] = f.R.hol[2] = 9; f.L.hol[3] = f.R.hol[3] = 6;
      f.L.cy -= 1; f.R.cy -= 1;
      setMouth(f, 9, mBigTop, mBigBot);
      break;
    case ACT_LOOK_DOWN_SMIRK: look(f, 0, 2); setMouth(f, 7, mSmirk, mSmirk); break;
    default: break;
  }
}

// ===== 표정별 대기 애니메이션 (계단식) =====
void OrbitFace::computeIdle(unsigned long now, int8_t idle[6]) {
  static const int8_t HAPPY_DY[4]   = { 0, -1, -2, -1 };
  static const int8_t SAD_TEAR[12]  = { 0, 0, 2, 4, 6, 8, 10, 12, -1, -1, -1, -1 };
  static const int8_t ANGRY_DX[4]   = { 0, 1, 0, -1 };
  static const int8_t CALM_LID[4]   = { 0, 1, 2, 1 };
  static const int8_t LISTEN_RY[6]  = { 0, 1, 2, 1, 0, -1 };

  memset(idle, 0, 6);
  unsigned long t = now - exprStartTime;
  switch (currentExpr) {
    case EXPR_NORMAL:    idle[ID_RY]   = rnd(0.6f * sinf(t * (2 * PI / 3200.0f))); break;  // 숨쉬기
    case EXPR_HAPPY:     idle[ID_DY]   = HAPPY_DY[(t / HAPPY_BOUNCE_MS) % 4]; break;       // 통통
    case EXPR_SAD:       idle[ID_TEAR] = SAD_TEAR[(t / SAD_TEAR_MS) % 12]; break;          // 눈물
    case EXPR_ANGRY:     idle[ID_DX]   = ANGRY_DX[(t / ANGRY_SHAKE_MS) % 4]; break;        // 부들부들
    case EXPR_CALM:      idle[ID_LID]  = CALM_LID[(t / CALM_BREATH_MS) % 4]; break;        // 느린 숨
    case EXPR_LISTENING: idle[ID_RY]   = LISTEN_RY[(t / LISTEN_PULSE_MS) % 6]; break;      // 귀 기울임
    case EXPR_THINKING:  idle[ID_DOTS] = (t / THINK_DOTS_MS) % 4; break;                   // 말줄임표
    default: break;
  }
}

// ===== 생성/초기화 =====
OrbitFace::OrbitFace()
  : u8g2(U8G2_R0, U8X8_PIN_NONE),
    currentExpr(EXPR_NORMAL),
    specialExpr(EXPR_DIZZY),
    mode(MODE_SHAPE),
    lidStep(0),
    forceDraw(true),
    lastFrameTime(0),
    exprStartTime(0),
    animFrame(0),
    lastAnimTime(0),
    lastBlinkTime(0),
    blinkInterval(3000),
    isBlinking(false),
    blinkStartTime(0),
    blinkDuration(0),
    blinkCount(0),
    action(-1),
    actionEndTime(0),
    nextActionTime(3000),
    statStart(0), statSumUs(0), statMaxUs(0), lastUpdateUs(0), loopMaxUs(0),
    statFrames(0) {
  baseShape(EXPR_NORMAL, cur);
  drawn = cur;
  memset(drawnIdle, 0, sizeof(drawnIdle));
}

void OrbitFace::begin() {
  Wire.begin(21, 22);
  u8g2.begin();
  u8g2.setContrast(255);

  // OLED 1프레임 그리는 시간 측정 (애니메이션 간격 조정용)
  int8_t idle[6] = { 0 };
  baseShape(EXPR_NORMAL, cur);
  unsigned long t0 = micros();
  drawShape(cur, idle);
  unsigned long us = micros() - t0;
  Serial.printf("[Face] 1프레임 그리기 %lu ms (%lu us)\n", us / 1000, us);
  statStart = millis();
}

// ===== 표정 변경 =====
void OrbitFace::setExpression(FaceExpression expr) {
  unsigned long now = millis();

  if (expr == EXPR_BLINK) {               // 표정은 그대로 두고 한 번 깜빡임
    if (mode == MODE_SHAPE && !isBlinking) {
      isBlinking = true; blinkCount = 1;
      blinkStartTime = now; blinkDuration = random(120, 220);
    }
    return;
  }
  if (expr == currentExpr) return;

  currentExpr = expr;
  exprStartTime = now;
  action = -1;
  nextActionTime = now + random(1500, 4000);
  isBlinking = false;
  lastBlinkTime = now;

  bool showingSpecial = (mode == MODE_SPECIAL_OPEN || mode == MODE_SPECIAL);
  if (isSpecial(expr)) {
    specialExpr = expr;
    if (showingSpecial || mode == MODE_SPECIAL_CLOSE) {   // 특수 → 특수: 눈꺼풀 열기부터
      mode = MODE_SPECIAL_OPEN; lidStep = 0; animFrame = 0;
    } else {
      mode = MODE_TO_SPECIAL;                             // 눈을 감은 뒤 특수 표정으로
    }
  } else {
    if (showingSpecial) { mode = MODE_SPECIAL_CLOSE; lidStep = 0; }   // 눈꺼풀 닫고 모양 변형으로
    else if (mode != MODE_SPECIAL_CLOSE) mode = MODE_SHAPE;
  }
  lastFrameTime = now - FRAME_MS;   // 다음 update()에서 바로 반응
}

// ===== 매 loop =====
void OrbitFace::update() {
  unsigned long now = millis();

#if FACE_STATS_ENABLED
  unsigned long us = micros();
  if (lastUpdateUs != 0 && us - lastUpdateUs > loopMaxUs) loopMaxUs = us - lastUpdateUs;
  lastUpdateUs = us;
  printStats(now);
#endif

  if (now - lastFrameTime < FRAME_MS) return;
  lastFrameTime = now;

  if (mode == MODE_SHAPE) stepShape(now);
  else stepSpecial(now);
}

void OrbitFace::stepShape(unsigned long now) {
  FaceShape tgt;
  baseShape(currentExpr, tgt);

  if (currentExpr == EXPR_NORMAL) {
    // 랜덤 행동 고르기 / 끝내기
    if (action < 0 && !isBlinking && (long)(now - nextActionTime) >= 0) {
      int8_t a = random(0, ACT_COUNT);
      if (a == ACT_DOUBLE_BLINK) {
        isBlinking = true; blinkCount = 2;
        blinkStartTime = now; blinkDuration = 120;
        nextActionTime = now + random(2000, 6000);
      } else {
        action = a;
        actionEndTime = now + random(900, 1800);
      }
    } else if (action >= 0 && (long)(now - actionEndTime) >= 0) {
      action = -1;
      nextActionTime = now + random(1500, 5000);
    }
    if (action >= 0) applyAction(action, tgt);

    // 평상시 깜빡임 (2.5~5초)
    if (!isBlinking && now - lastBlinkTime > blinkInterval) {
      isBlinking = true; blinkCount = 1;
      blinkStartTime = now; blinkDuration = random(120, 220);
    }
  } else if (currentExpr == EXPR_THINKING) {
    // 위쪽 오른쪽 ↔ 왼쪽 번갈아 보기 (4.8초 주기)
    unsigned long tt = (now - exprStartTime) % 4800;
    float g = (tt < 2000) ? 0 : (tt < 2150) ? -2 : (tt < 3600) ? -4 : (tt < 3750) ? -2 : 0;
    tgt.L.cx += g; tgt.R.cx += g;
  }

  // 깜빡임 진행 (두 번 깜빡임은 사이에 140ms 뜸)
  if (isBlinking) {
    unsigned long bt = now - blinkStartTime;
    if (bt < blinkDuration) {
      tgt.L.ry = tgt.R.ry = 1;
    } else if (blinkCount > 1) {
      if (bt >= blinkDuration + 140) { blinkCount--; blinkStartTime = now; }
    } else {
      isBlinking = false;
      lastBlinkTime = now;
      blinkInterval = random(2500, 5000);
    }
  }

  float k = (isBlinking || fabsf(cur.L.ry - tgt.L.ry) > 3) ? FAST_K : MORPH_K;
  lerpShape(cur, tgt, k);
  if (maxDiff(cur, tgt) < 0.05f) cur = tgt;   // 다 왔으면 정확히 맞춤

  int8_t idle[6];
  computeIdle(now, idle);

  float d = maxDiff(cur, drawn);
  bool settledChanged = (d > 0) && (maxDiff(cur, tgt) == 0);
  if (forceDraw || d > REDRAW_DIFF || settledChanged || memcmp(idle, drawnIdle, 6) != 0) {
    drawShape(cur, idle);
    drawn = cur;
    memcpy(drawnIdle, idle, 6);
    forceDraw = false;
  }
}

void OrbitFace::stepSpecial(unsigned long now) {
  static const int8_t OPEN_H[3]  = { 2, 5, 9 };
  static const int8_t CLOSE_H[4] = { 9, 5, 2, -1 };

  switch (mode) {
    case MODE_TO_SPECIAL: {          // 지금 모양에서 눈을 감음
      FaceShape tgt;
      closedShape(tgt);
      lerpShape(cur, tgt, FAST_K);
      int8_t idle[6] = { 0 };
      drawShape(cur, idle);
      drawn = cur;
      memset(drawnIdle, 0, sizeof(drawnIdle));
      if (maxDiff(cur, tgt) < 0.6f) {
        mode = MODE_SPECIAL_OPEN; lidStep = 0;
        animFrame = 0; lastAnimTime = now;
      }
      break;
    }
    case MODE_SPECIAL_OPEN:          // 눈꺼풀 열며 특수 표정 등장
      drawSpecial(OPEN_H[lidStep]);
      if (++lidStep >= 3) { mode = MODE_SPECIAL; lastAnimTime = now; }
      break;

    case MODE_SPECIAL: {
      uint16_t interval = (specialExpr == EXPR_DIZZY) ? DIZZY_FRAME_MS : SLEEP_FRAME_MS;
      if (now - lastAnimTime >= interval) {
        lastAnimTime = now;
        animFrame++;
        drawSpecial(LID_NONE);
      }
      break;
    }
    case MODE_SPECIAL_CLOSE:         // 눈꺼풀 닫은 뒤 감은 눈에서 새 표정으로 변형
      drawSpecial(CLOSE_H[lidStep]);
      if (++lidStep >= 4) {
        closedShape(cur);
        mode = MODE_SHAPE;
        forceDraw = true;
      }
      break;

    default: break;
  }
}

// ===== 그리기 =====
void OrbitFace::drawShape(const FaceShape& f, const int8_t idle[6]) {
  u8g2.clearBuffer();
  int jx = idle[ID_DX], jy = idle[ID_DY];

  for (int side = 0; side < 2; side++) {
    int s = side ? 1 : -1;
    const EyeShape& e = side ? f.R : f.L;
    int ox = XC + s * ES;                 // 눈 기본 x
    float cx = ox + e.cx + jx;
    float cy = YC + e.cy + jy;
    int icx = rnd(cx);

    int rx = max(1, rnd(e.rx));
    int ry = max(1, rnd(e.ry) + idle[ID_RY]);
    u8g2.drawFilledEllipse(icx, rnd(cy), rx, ry);

    u8g2.setDrawColor(0);
    if (e.hol[2] >= 0.6f && e.hol[3] >= 0.6f) {          // 안쪽 파내기
      u8g2.drawFilledEllipse(rnd(cx + e.hol[0]), rnd(YC + e.hol[1] + jy), rnd(e.hol[2]), rnd(e.hol[3]));
    }
    float tx = ox + e.cx + jx;                             // 비스듬히 잘라내기
    u8g2.drawTriangle(rnd(tx + e.tri[0]), rnd(YC + jy + e.tri[1]),
                      rnd(tx + e.tri[2]), rnd(YC + jy + e.tri[3]),
                      rnd(tx + e.tri[4]), rnd(YC + jy + e.tri[5]));
    int cb = rnd(YC + e.cutBot + jy);                      // 아래 자르기
    if (cb < 64) u8g2.drawBox(icx - 14, max(0, cb), 29, 64 - max(0, cb));
    int ct = rnd(YC + e.cutTop + jy) + idle[ID_LID];       // 위 자르기
    int topY = max(0, YC - 20 + jy);
    if (ct > topY) u8g2.drawBox(icx - 14, topY, 29, ct - topY);
    u8g2.setDrawColor(1);

    if (e.lid >= 0.5f) u8g2.drawHLine(icx - 10, ct, 21);   // 눈꺼풀 선

    int bt = rnd(e.brow[4]);                               // 눈썹
    for (int o = 0; o < bt; o++) {
      u8g2.drawLine(rnd(tx + e.brow[0]), rnd(YC + jy + e.brow[1]) + o,
                    rnd(tx + e.brow[2]), rnd(YC + jy + e.brow[3]) + o);
    }

    if (f.cheek >= 0.5f) {                                 // 볼터치 /// (고정 위치)
      for (int k = 0; k < 3; k++) u8g2.drawLine(ox - 6 + k * 4, YC + 14, ox - 4 + k * 4, YC + 11);
    }
  }

  if (f.tear >= 0.5f && idle[ID_TEAR] >= 0) {              // 눈물
    u8g2.drawFilledEllipse(XC + ES + 10 + jx, YC + 12 + idle[ID_TEAR], 2, 3);
  }
  if (f.dots >= 0.5f) {                                    // 말줄임표
    for (int k = 0; k < idle[ID_DOTS]; k++) u8g2.drawDisc(XC + 44 + k * 6, YC - 22, 1);
  }

  drawMouth(f, jx, jy);
  sendFrame();
}

void OrbitFace::drawMouth(const FaceShape& f, int dx, int dy) {
  if (f.w < 0.5f) return;
  int hw = rnd(f.w);
  int bx = XC + rnd(f.mx) + dx;
  int by = MY + rnd(f.my) + dy;
  for (int x = -hw; x <= hw; x++) {
    float p = ((float)x / f.w + 1) * 0.5f * (MOUTH_PTS - 1);
    p = constrain(p, 0.0f, (float)(MOUTH_PTS - 1));
    int i = min((int)p, MOUTH_PTS - 2);
    float fr = p - i;
    float t = f.top[i] + (f.top[i + 1] - f.top[i]) * fr;
    float b = f.bot[i] + (f.bot[i + 1] - f.bot[i]) * fr;
    int y0 = (int)floorf(t + 0.5f);
    int y1 = (int)floorf(fmaxf(t, b) + 0.5f);
    u8g2.drawVLine(bx + x, by + y0, y1 - y0 + 1);
  }
}

static void zGlyph(U8G2& g, int x, int y, int s) {   // 작은 z
  g.drawHLine(x, y, s);
  g.drawLine(x + s - 1, y, x, y + s - 1);
  g.drawHLine(x, y + s - 1, s);
}

// 특수 표정 (DIZZY, SLEEP). lidH: 눈꺼풀 가림 높이 (LID_NONE=없음, -1=완전히 감김)
void OrbitFace::drawSpecial(int lidH) {
  u8g2.clearBuffer();

  if (specialExpr == EXPR_DIZZY) {
    // 소용돌이 눈 (프레임마다 회전, 양쪽 눈은 반대 방향)
    for (int side = 0; side < 2; side++) {
      int cx = side ? XC + ES : XC - ES;
      float dir = side ? -1.0f : 1.0f;
      int px = 0, py = 0;
      for (int i = 0; i < 64; i++) {
        float t = i * 0.2f;
        float r = 0.75f * t + 0.5f;
        float a = dir * (t + animFrame * 0.9f);
        int x = (int)lroundf(cx + r * cosf(a));
        int y = (int)lroundf(YC + r * sinf(a));
        if (i > 0) u8g2.drawLine(px, py, x, y);
        px = x; py = y;
      }
    }
    // 꿈틀거리는 물결 입
    int px = 0, py = 0;
    for (int i = 0; i <= 20; i++) {
      int x = XC - 10 + i;
      int y = MY - 1 + (int)lroundf(1.5f * sinf(i * 0.9f + animFrame));
      if (i > 0) u8g2.drawLine(px, py, x, y);
      px = x; py = y;
    }
  } else {
    // 자는 눈 (u u) + 숨쉬기 + 떠오르는 zZ
    int dy = (animFrame / 4) % 2;
    int y = YC + dy;
    for (int side = 0; side < 2; side++) {
      int cx = side ? XC + ES : XC - ES;
      u8g2.drawLine(cx - 7, y, cx - 3, y + 4);
      u8g2.drawLine(cx - 7, y + 1, cx - 3, y + 5);
      u8g2.drawHLine(cx - 3, y + 4, 6);
      u8g2.drawHLine(cx - 3, y + 5, 6);
      u8g2.drawLine(cx + 3, y + 4, cx + 7, y);
      u8g2.drawLine(cx + 3, y + 5, cx + 7, y + 1);
    }
    u8g2.drawLine(XC - 8, MY - 3 + dy, XC, MY + dy);
    u8g2.drawLine(XC, MY + dy, XC + 8, MY - 3 + dy);
    int k = animFrame % 8;
    zGlyph(u8g2, XC + 26 + k, YC - 8 - k * 2, 4);
    int k2 = (k + 4) % 8;
    zGlyph(u8g2, XC + 26 + k2, YC - 8 - k2 * 2, 6);
  }

  if (lidH != LID_NONE) {   // 눈 영역(0~37행)을 위아래에서 가림
    u8g2.setDrawColor(0);
    for (int y = 0; y < 38; y++) {
      if (lidH < 0 || abs(y - YC) > lidH) u8g2.drawHLine(0, y, 128);
    }
    u8g2.setDrawColor(1);
    if (lidH < 0) {
      u8g2.drawHLine(XC - ES - 8, YC, 16);
      u8g2.drawHLine(XC + ES - 8, YC, 16);
    }
  }
  sendFrame();
}

void OrbitFace::sendFrame() {
  unsigned long t0 = micros();
  u8g2.sendBuffer();
  unsigned long d = micros() - t0;
  statSumUs += d;
  if (d > statMaxUs) statMaxUs = d;
  statFrames++;
}

void OrbitFace::printStats(unsigned long now) {
  if (now - statStart < STATS_PERIOD_MS) return;
  if (statFrames > 0) {
    Serial.printf("[Face] 5초 통계: %u프레임, 전송 평균 %.1f ms / 최대 %.1f ms, loop 최대 간격 %.1f ms\n",
                  statFrames, statSumUs / 1000.0f / statFrames, statMaxUs / 1000.0f, loopMaxUs / 1000.0f);
  } else {
    Serial.printf("[Face] 5초 통계: 0프레임, loop 최대 간격 %.1f ms\n", loopMaxUs / 1000.0f);
  }
  statStart = now; statSumUs = 0; statMaxUs = 0; statFrames = 0; loopMaxUs = 0;
}

// ===== 기상 / 수면 연출 =====
// 부팅/기상 시 감은 눈에서 서서히 눈뜨는 연출 (약 0.4~0.5초)
void OrbitFace::playWakeupAnimation() {
  FaceShape tgt;
  baseShape(EXPR_NORMAL, tgt);
  closedShape(cur);
  int8_t idle[6] = { 0 };
  for (int i = 0; i < 8; i++) {
    lerpShape(cur, tgt, 0.4f);
    drawShape(cur, idle);
    delay(FRAME_MS);
  }
  cur = tgt;
  drawShape(cur, idle);
  drawn = cur;
  memset(drawnIdle, 0, sizeof(drawnIdle));
  currentExpr = EXPR_NORMAL;
  mode = MODE_SHAPE;
  unsigned long now = millis();
  exprStartTime = now;
  lastBlinkTime = now;
  nextActionTime = now + random(1500, 4000);
}

// 딥슬립 진입 전 잠드는 연출 (눈 감고 자는 표정 약 4초 후 OLED 절전)
void OrbitFace::playSleepAnimation() {
  setExpression(EXPR_SLEEP);
  unsigned long t0 = millis();
  while (millis() - t0 < 4000) {
    update();
    delay(5);
  }
  u8g2.clearBuffer();
  u8g2.sendBuffer();
  u8g2.setPowerSave(1); // OLED 패널 전원 절전 모드
}
