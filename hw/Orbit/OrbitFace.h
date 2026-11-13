#ifndef ORBIT_FACE_H
#define ORBIT_FACE_H

#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

// 표정 상태 정의 (번호가 로그에 찍히므로 순서 유지, 새 표정은 끝에 추가)
enum FaceExpression {
  EXPR_NORMAL,    // 평상시 (랜덤 행동: 두리번, 입 모양 변화, 갸웃, 눈웃음 등)
  EXPR_BLINK,     // 눈 깜빡임 (표정은 그대로 두고 한 번 깜빡임)
  EXPR_HAPPY,     // 기쁨/쓰다듬기
  EXPR_SAD,       // 슬픔
  EXPR_SLEEP,     // 수면 모드
  EXPR_DIZZY,     // 어지러움
  EXPR_LISTENING, // 음성 수신 중
  EXPR_THINKING,  // 생각 중
  EXPR_ANGRY,     // 화남
  EXPR_CALM       // 차분함
};

// 표정 모양을 숫자로 표현 (전환할 때 두 표정의 숫자를 섞어서 부드럽게 변형)
// 모든 멤버가 float 이어야 함 (배열처럼 한꺼번에 섞기 때문)
struct EyeShape {
  float cx, cy, rx, ry;   // 눈 타원: 기본 위치에서의 이동량, 반지름
  float tri[6];           // 지울 삼각형 (눈 기본 x, y_center 기준)
  float hol[4];           // 지울 타원 (x는 눈 기준, y는 y_center 기준), 반지름
  float cutBot;           // 이 높이(y_center 기준)부터 아래를 지움
  float cutTop;           // 이 높이(y_center 기준) 위를 지움
  float lid;              // 0.5 이상이면 cutTop 위치에 눈꺼풀 선
  float brow[5];          // 눈썹 x1, y1, x2, y2, 두께
};

static const int MOUTH_PTS = 9;   // 입 곡선 점 개수

struct FaceShape {
  EyeShape L, R;
  float w, mx, my;                // 입 반폭, 입 이동량
  float top[MOUTH_PTS];           // 입 윗선 높이 (mouth_y 기준)
  float bot[MOUTH_PTS];           // 입 아랫선 높이 (윗선~아랫선 사이를 채움)
  float cheek, tear, dots;        // 0.5 이상이면 표시
};

class OrbitFace {
private:
  U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2;
  FaceExpression currentExpr;
  FaceExpression specialExpr;   // 지금 화면에 그리는 특수 표정 (DIZZY/SLEEP)

  // 상태 (모양 변형 / 특수 표정 전환)
  enum Mode : uint8_t { MODE_SHAPE, MODE_TO_SPECIAL, MODE_SPECIAL_OPEN, MODE_SPECIAL, MODE_SPECIAL_CLOSE };
  Mode mode;
  uint8_t lidStep;

  FaceShape cur;        // 지금 화면 모양 (목표 쪽으로 조금씩 다가감)
  FaceShape drawn;      // 마지막으로 화면에 보낸 모양
  int8_t drawnIdle[6];  // 마지막으로 보낸 대기 애니메이션 값
  bool forceDraw;

  unsigned long lastFrameTime;
  unsigned long exprStartTime;
  uint8_t animFrame;            // 특수 표정(DIZZY, SLEEP) 프레임 번호
  unsigned long lastAnimTime;

  // 깜빡임
  unsigned long lastBlinkTime;
  unsigned long blinkInterval;
  bool isBlinking;
  unsigned long blinkStartTime;
  unsigned long blinkDuration;
  uint8_t blinkCount;           // 남은 깜빡임 횟수 (두 번 깜빡임용)

  // NORMAL 랜덤 행동
  int8_t action;                // -1 = 행동 없음
  unsigned long actionEndTime;
  unsigned long nextActionTime;

  // 전송 시간 측정
  unsigned long statStart, statSumUs, statMaxUs, lastUpdateUs, loopMaxUs;
  uint16_t statFrames;

  static bool isSpecial(FaceExpression e) { return e == EXPR_DIZZY || e == EXPR_SLEEP; }
  void baseShape(FaceExpression e, FaceShape& f);
  void closedShape(FaceShape& f);
  void applyAction(int8_t a, FaceShape& f);
  void computeIdle(unsigned long now, int8_t idle[6]);
  void stepShape(unsigned long now);
  void stepSpecial(unsigned long now);
  void drawShape(const FaceShape& f, const int8_t idle[6]);
  void drawSpecial(int lidH);
  void drawMouth(const FaceShape& f, int dx, int dy);
  void sendFrame();
  void printStats(unsigned long now);

public:
  OrbitFace();
  void begin();
  void setExpression(FaceExpression expr); // 표정 변경 (부드럽게 전환)
  void update();                           // 매 loop 호출: 전환/대기 애니메이션/깜빡임
  void playWakeupAnimation();              // 기상 시 서서히 눈뜨는 애니메이션
  void playSleepAnimation();               // 딥슬립 전 잠드는 연출 및 화면 끄기
};

#endif
