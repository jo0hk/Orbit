// 음성 교신: 녹음 -> AI 서버 POST -> 응답 JSON 적용 -> 응답 음성 재생
// 모든 블로킹 작업은 별도 태스크(core 0)에서 수행하고,
// OLED/LED/진동은 큐를 통해 메인 루프(voiceUpdate)에서만 바꿉니다.

#include "voice_client.h"
#include "config.h"
#include "audio_in.h"
#include "audio_out.h"
#include "light_sensor.h"
#include "hardware_action.h"
#include "json_pipeline.h"
#include "non_blocking_hw.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <LittleFS.h>
#include <ArduinoJson.h>

#define REC_PATH        "/rec.wav"
#define VOICE_STACK     12288
#define CONNECT_TIMEOUT_MS 5000

enum UiEventType : uint8_t {
  UI_LISTENING,   // 녹음 시작
  UI_THINKING,    // AI 응답 대기
  UI_APPLY,       // 응답 JSON 적용
  UI_NO_SPEECH,   // 말 없음 / 취소
  UI_ERROR,       // 실패
  UI_DONE         // 세션 종료
};

struct UiEvent {
  UiEventType type;
  char json[160];
};

static QueueHandle_t uiQueue = nullptr;
static TaskHandle_t voiceTask = nullptr;
static volatile VoiceState state = VOICE_IDLE;
static volatile bool stopRequested = false;
static String devId;
static bool ready = false;

// 메인 루프 쪽 상태: LISTENING/THINKING 표정을 띄운 뒤 아직 응답 표정으로 안 바뀌었는지
static bool waitingExprActive = false;

static void postUi(UiEventType type, const char* json = nullptr) {
  UiEvent e;
  e.type = type;
  e.json[0] = '\0';
  if (json) strlcpy(e.json, json, sizeof(e.json));
  xQueueSend(uiQueue, &e, 0);   // 가득 차면 버림 (표시용)
}

static void failSession(const char* reason) {
  Serial.printf("[Voice] 실패: %s\n", reason);
  postUi(UI_ERROR);
  audioOutTone(220, 300);
}

// ── HTTP: multipart 업로드 후 응답 본문 수신. 반환: HTTP 상태코드 또는 음수(통신 오류) ──
static int postVoice(int lux, const String& requestId, String& body) {
  File f = LittleFS.open(REC_PATH, "r");
  if (!f) return -10;

  String boundary = "----OrbitBoundary" + String((uint32_t)esp_random(), HEX);
  String head;
  auto addField = [&](const char* name, const String& value) {
    head += "--" + boundary + "\r\nContent-Disposition: form-data; name=\"" + name + "\"\r\n\r\n" + value + "\r\n";
  };
  addField("device_id", devId);
  if (lux >= 0) addField("lux", String(lux));
  addField("request_id", requestId);
  head += "--" + boundary +
          "\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"rec.wav\"\r\nContent-Type: audio/wav\r\n\r\n";
  String tail = "\r\n--" + boundary + "--\r\n";
  size_t total = head.length() + f.size() + tail.length();

  WiFiClient client;
  if (!client.connect(AI_SERVER_HOST, AI_SERVER_PORT, CONNECT_TIMEOUT_MS)) { f.close(); return -1; }

  client.printf("POST /api/v1/interact/voice HTTP/1.1\r\n"
                "Host: %s:%d\r\n"
                "Content-Type: multipart/form-data; boundary=%s\r\n"
                "Content-Length: %u\r\n"
                "Connection: close\r\n\r\n",
                AI_SERVER_HOST, AI_SERVER_PORT, boundary.c_str(), (unsigned)total);
  client.print(head);

  uint8_t buf[1024];
  while (f.available()) {
    size_t n = f.read(buf, sizeof(buf));
    if (n == 0 || client.write(buf, n) != n) { f.close(); client.stop(); return -2; }
  }
  f.close();
  client.print(tail);

  // 응답 대기 (STT + LLM + TTS)
  unsigned long t0 = millis();
  while (!client.available()) {
    if (!client.connected()) { client.stop(); return -3; }
    if (millis() - t0 > AI_HTTP_TIMEOUT_MS) { client.stop(); return -4; }
    vTaskDelay(pdMS_TO_TICKS(20));
  }

  // 상태줄: "HTTP/1.1 200 OK"
  String status = client.readStringUntil('\n');
  int code = (status.length() >= 12) ? status.substring(9, 12).toInt() : 0;

  int contentLen = -1;
  bool chunked = false;
  while (true) {
    String line = client.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) break;
    line.toLowerCase();
    if (line.startsWith("content-length:")) contentLen = line.substring(15).toInt();
    else if (line.startsWith("transfer-encoding:") && line.indexOf("chunked") >= 0) chunked = true;
  }
  if (chunked) { client.stop(); return -5; }   // FastAPI JSON 응답은 Content-Length 사용 (예외 대비)

  body = "";
  unsigned long last = millis();
  while ((contentLen < 0 || (int)body.length() < contentLen) && millis() - last < 5000) {
    while (client.available()) { body += (char)client.read(); last = millis(); }
    if (!client.connected() && !client.available()) break;
    vTaskDelay(1);
  }
  client.stop();
  return code;
}

// ── 응답 JSON에서 HW 신호만 뽑아 메인 루프로 넘기고, audio_url 반환 ──
static bool handleResponse(const String& body, String& audioUrl) {
#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument filter, doc, cmd;
#else
  StaticJsonDocument<128> filter;
  StaticJsonDocument<512> doc;
  StaticJsonDocument<192> cmd;
#endif
  filter["led"] = true;
  filter["vibe"] = true;
  filter["oled_expression"] = true;
  filter["audio_url"] = true;

  DeserializationError err = deserializeJson(doc, body, DeserializationOption::Filter(filter));
  if (err) {
    Serial.printf("[Voice] 응답 파싱 실패: %s\n", err.c_str());
    return false;
  }

  if (doc["led"].is<const char*>())             cmd["led"]  = doc["led"].as<const char*>();
  if (doc["vibe"].is<const char*>())            cmd["vibe"] = doc["vibe"].as<const char*>();
  if (doc["oled_expression"].is<const char*>()) cmd["oled"] = doc["oled_expression"].as<const char*>();

  char out[160];
  serializeJson(cmd, out, sizeof(out));
  postUi(UI_APPLY, out);

  audioUrl = doc["audio_url"].is<const char*>() ? doc["audio_url"].as<String>() : "";
  return true;
}

// ── 응답 음성 다운로드하면서 재생 ──
static bool playAudioUrl(const String& url) {
  String full = url;
  if (!full.startsWith("http")) {   // "outputs/x.wav" 같은 상대 경로면 AI 서버 기준으로
    full = String("http://") + AI_SERVER_HOST + ":" + AI_SERVER_PORT + (url.startsWith("/") ? "" : "/") + url;
  }
  HTTPClient http;
  if (!http.begin(full)) return false;
  int code = http.GET();
  if (code != 200) {
    Serial.printf("[Voice] 음성 다운로드 실패 %d: %s\n", code, full.c_str());
    http.end();
    return false;
  }
  WiFiClient* stream = http.getStreamPtr();
  bool ok = (stream != nullptr) && audioOutPlayWav(*stream, &stopRequested);
  http.end();
  return ok;
}

static void runSession() {
  if (WiFi.status() != WL_CONNECTED) { failSession("Wi-Fi 미연결"); return; }

  // 1) 녹음
  state = VOICE_LISTENING;
  postUi(UI_LISTENING);
  audioOutTone(880, 120);   // 시작음

  uint32_t bytes = 0;
  RecordResult rec = audioInRecord(REC_PATH, &stopRequested, &bytes);
  stopRequested = false;
  if (rec == REC_NO_SPEECH) {
    Serial.println("[Voice] 말 없음 -> 취소");
    postUi(UI_NO_SPEECH);
    audioOutTone(440, 150);
    return;
  }
  if (rec != REC_OK) { failSession("녹음 오류"); return; }
  audioOutTone(660, 100);   // 녹음 끝 알림

  // 2) AI 서버 전송
  state = VOICE_PROCESSING;
  postUi(UI_THINKING);
  int lux = lightReadLux();
  String requestId = devId + "-" + String((uint32_t)esp_random(), HEX);
  String body;
  unsigned long t0 = millis();
  int code = postVoice(lux, requestId, body);
  LittleFS.remove(REC_PATH);
  Serial.printf("[Voice] 응답 %d (%lums)\n", code, millis() - t0);
  if (code != 200) {
    if (code > 0) Serial.printf("[Voice] 서버 응답: %s\n", body.c_str());
    failSession(code == -4 ? "응답 시간 초과" : code < 0 ? "서버 연결 실패" : "서버 오류");
    return;
  }

  // 3) 신호 적용 + 음성 재생
  String audioUrl;
  if (!handleResponse(body, audioUrl)) { failSession("응답 형식 오류"); return; }
  if (audioUrl.length() == 0) {
    Serial.println("[Voice] audio_url 없음 -> 신호만 적용");
    return;
  }
  state = VOICE_PLAYING;
  if (!playAudioUrl(audioUrl)) Serial.println("[Voice] 음성 재생 실패 (wav 형식·다운로드 경로 확인)");
  stopRequested = false;
}

static void voiceTaskFn(void*) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);   // 더블탭 대기
    stopRequested = false;
    runSession();
    state = VOICE_IDLE;
    postUi(UI_DONE);
  }
}

bool voiceBegin(const char* deviceId) {
  devId = deviceId;
  if (!LittleFS.begin(true)) {   // 처음이면 포맷
    Serial.println("[Voice] LittleFS 마운트 실패");
    return false;
  }
  LittleFS.remove(REC_PATH);     // 이전에 남은 녹음 정리

  bool micOk = audioInBegin();
  bool spkOk = audioOutBegin();
  lightBegin();
  if (!micOk || !spkOk) return false;

  uiQueue = xQueueCreate(8, sizeof(UiEvent));
  if (!uiQueue) return false;
  if (xTaskCreatePinnedToCore(voiceTaskFn, "voice", VOICE_STACK, nullptr, 1, &voiceTask, 0) != pdPASS) {
    Serial.println("[Voice] 태스크 생성 실패");
    return false;
  }
  ready = true;
  Serial.println("[Voice] 음성 교신 준비 완료 (더블탭으로 시작)");
  return true;
}

void voiceOnDoubleTap() {
  if (!ready) return;
  switch (state) {
    case VOICE_IDLE:
      state = VOICE_LISTENING;   // 중복 시작 방지 (태스크가 곧 다시 설정)
      xTaskNotifyGive(voiceTask);
      break;
    case VOICE_LISTENING:
    case VOICE_PLAYING:
      stopRequested = true;      // 녹음 종료 / 재생 중단
      break;
    case VOICE_PROCESSING:
      break;                     // 응답 대기 중엔 무시
  }
}

bool voiceIsBusy() {
  return state != VOICE_IDLE;
}

void voiceUpdate() {
  if (!uiQueue) return;
  UiEvent e;
  while (xQueueReceive(uiQueue, &e, 0) == pdTRUE) {
    switch (e.type) {
      case UI_LISTENING:
        setExpression(EXPR_LISTENING, 0);
        waitingExprActive = true;
        break;
      case UI_THINKING:
        setExpression(EXPR_THINKING, 0);
        waitingExprActive = true;
        break;
      case UI_APPLY:
        Serial.printf("[Voice] 신호 적용: %s\n", e.json);
        parseAndExecuteJson(String(e.json));
        if (strstr(e.json, "\"oled\"")) waitingExprActive = false;   // 응답 표정으로 바뀜
        break;
      case UI_NO_SPEECH:
        setExpression(EXPR_NORMAL, 0);
        waitingExprActive = false;
        break;
      case UI_ERROR:
        setExpression(EXPR_SAD, 2000);
        triggerVibration(VIBE_SHORT);
        waitingExprActive = false;
        break;
      case UI_DONE:
        if (waitingExprActive) setExpression(EXPR_NORMAL, 0);   // 응답 표정이 없었으면 평상시로
        waitingExprActive = false;
        break;
    }
  }
}
