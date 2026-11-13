"""파이프라인-백엔드 연동 테스트.

모델(STT·감정·Gemini·TTS)은 가짜로 바꾸고, 백엔드는 httpx.MockTransport로 흉내 냅니다.
실제 모델과 API 키가 필요한 경로는 여기서 확인하지 않습니다.
"""

import asyncio
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.interact import router
from app.core.pipeline import OrbitCore
from app.missions import Channel
from app.schemas import (
    CommonEmotion,
    Emotion,
    Led,
    MissionResult,
    OledExpression,
    Vibe,
)
from tests.fakes import (
    FAKE_MISSION,
    FAKE_MOOD_MISSION,
    FakeBackend,
    FakeEmotion,
    FakeLLM,
    FakeSTT,
    FakeTTS,
    device_routes,
    ok,
)


def make_core(fake: FakeBackend | None, *, text="밖에 비가 와", emotion=Emotion.NEUTRAL,
              stt_conf=0.9, llm_fail=False) -> OrbitCore:
    core = OrbitCore(backend=fake.client() if fake else None)
    core.stt = FakeSTT(text, stt_conf)
    core.emotion = FakeEmotion(emotion)
    core.llm = FakeLLM(fail=llm_fail)
    core.tts = FakeTTS()
    return core


def voice(core: OrbitCore, **kw):
    return asyncio.run(core.interact_voice("dummy.wav", device_id="ORBIT-001", **kw))


def text_turn(core: OrbitCore, text: str, **kw):
    return asyncio.run(core.interact_text(text, user_id=3, **kw))


def mood_routes():
    return {
        ("GET", "/api/missions/current"): ok(FAKE_MOOD_MISSION),
        ("POST", "/api/missions/11/result"): ok(FAKE_MOOD_MISSION),
        ("POST", "/api/conversations"): ok({}),
    }


# ─── 키링 음성 ───────────────────────────────────────────────
def test_voice_weather_mission_success():
    fake = FakeBackend(device_routes(FAKE_MISSION))
    core = make_core(fake, text="밖에 비가 와", emotion=Emotion.SAD)
    out = voice(core, lux=120)

    res = out.response
    assert res.mission_result is MissionResult.SUCCESS
    # 성공 턴은 사용자 감정(sad)과 무관하게 성공 신호
    assert (res.led, res.vibe, res.oled_expression) == (
        Led.RAINBOW, Vibe.STRONG_DOUBLE, OledExpression.HAPPY,
    )
    assert "[미션 반응 수칙 — 임무 성공]" in core.llm.prompts[0]
    assert "과장 톤을 한 단계 낮춰" in core.llm.prompts[0]
    assert core.tts.calls == 1
    assert res.request_id
    # 키링이 서버 주소를 앞에 붙여 내려받는 상대 경로 (main.py 가 /outputs 로 공개)
    assert res.audio_url.startswith("outputs/") and res.audio_url.endswith(".wav")
    assert "\\" not in res.audio_url

    rec = out.record
    assert (rec.user_id, rec.stage, rec.channel) == (3, 2, Channel.VOICE)
    assert rec.mission_turn.mission_id == 12
    assert rec.emotion is CommonEmotion.SAD
    # 응답 전에는 결과 API·대화 저장을 하지 않음 (백그라운드에서 함)
    assert not fake.called("POST", "/api/missions/12/result")
    assert not fake.called("POST", "/api/conversations")
    # 최근 대화는 아직 프롬프트에 쓰지 않아 조회하지 않음
    assert not any(p.endswith("/recent") for _, p in fake.paths())


def test_voice_without_mission_uses_emotion_signal():
    fake = FakeBackend(device_routes(mission=None))  # 오늘 미션 조회·배정 모두 404
    core = make_core(fake, text="그냥 심심해", emotion=Emotion.SAD)
    res = voice(core).response

    assert res.mission_result is MissionResult.NONE
    assert res.oled_expression is OledExpression.SAD  # 기존 감정 매핑
    assert res.led is Led.BLUE  # LLM 값 그대로
    assert "[미션 반응 수칙" not in core.llm.prompts[0]


def test_voice_backend_down_still_answers():
    fake = FakeBackend({})  # 모든 경로 404 = 등록 안 된 기기
    core = make_core(fake)
    out = voice(core)

    assert out.response.speech
    assert out.response.mission_result is MissionResult.NONE
    assert out.record.user_id is None


def test_voice_without_backend_client():
    core = make_core(None)
    out = voice(core)

    assert out.response.mission_result is MissionResult.NONE
    assert out.record.user_id is None


def test_high_risk_skips_mission_and_llm():
    fake = FakeBackend(device_routes(FAKE_MISSION))
    core = make_core(fake, text="비가 와서 죽고 싶어")
    out = voice(core)

    assert out.response.high_risk_detected
    assert out.response.mission_result is MissionResult.NONE
    assert out.record.mission_turn is None
    assert core.llm.prompts == []  # LLM 호출 안 함
    assert out.record.user_id == 3  # 고위험 턴도 대화는 저장 (conversation-log-spec 3절)


def test_llm_failure_keeps_emergency_signal_but_reports_judgement():
    fake = FakeBackend(device_routes(FAKE_MISSION))
    core = make_core(fake, llm_fail=True)
    out = voice(core)

    res = out.response
    assert res.fallback_triggered
    assert res.led is Led.BLUE and res.oled_expression is OledExpression.SAD  # 비상 신호 유지
    # 판정은 사용자 발화로 이미 끝났으므로 결과는 기록합니다
    assert out.record.mission_turn.judgement.result is MissionResult.SUCCESS


def test_tts_failure_still_answers_and_records():
    """음성 합성(외부 서비스)이 실패해도 대사·신호·기록은 정상이어야 합니다."""
    fake = FakeBackend(device_routes(FAKE_MISSION))
    core = make_core(fake)
    core.tts = FakeTTS(fail=True)
    out = voice(core)

    assert out.response.audio_url is None
    assert out.response.speech
    assert out.response.mission_result is MissionResult.SUCCESS
    assert out.record.user_id == 3


def test_outputs_route_serves_reply_audio():
    """main.py 가 응답 음성 폴더를 /outputs 로 공개하는지 확인합니다 (lifespan 미실행)."""
    from app.core.pipeline import OUTPUT_DIR
    from app.main import app

    f = OUTPUT_DIR / "pytest_route_check.wav"
    f.write_bytes(b"RIFF0000WAVE")
    try:
        client = TestClient(app)  # with 문을 쓰지 않아 모델 로딩(lifespan)을 하지 않음
        resp = client.get("/outputs/pytest_route_check.wav")
        assert resp.status_code == 200
        assert resp.content == b"RIFF0000WAVE"
        assert client.get("/outputs/../app/main.py").status_code == 404
    finally:
        f.unlink(missing_ok=True)


# ─── 앱 텍스트 ───────────────────────────────────────────────
def test_text_mood_mission_success_without_tts():
    fake = FakeBackend(mood_routes())
    core = make_core(fake)
    out = text_turn(core, "오늘 좀 피곤해", request_id="app-1")

    res = out.response
    assert res.mission_result is MissionResult.SUCCESS
    assert res.oled_expression is OledExpression.HAPPY
    assert res.audio_url is None
    assert core.tts.calls == 0
    assert res.request_id == "app-1"
    assert res.latency.stt_ms == 0
    assert (out.record.user_id, out.record.stage, out.record.channel) == (3, 1, Channel.TEXT)


def test_text_positive_expression_maps_to_happy():
    fake = FakeBackend(mood_routes())
    out = text_turn(make_core(fake), "오늘 기분 좋아")

    assert out.response.user_emotion is Emotion.NEUTRAL
    assert out.response.emotion is CommonEmotion.HAPPY


def test_text_does_not_judge_voice_mission():
    fake = FakeBackend({
        ("GET", "/api/missions/current"): ok(FAKE_MISSION),  # 2단계 = 음성 미션
    })
    out = text_turn(make_core(fake), "밖에 비가 와")

    assert out.response.mission_result is MissionResult.NONE


# ─── 엔드포인트 (응답 후 백그라운드 기록) ────────────────────
@pytest.fixture
def api():
    def _make(fake: FakeBackend, **core_kw):
        app = FastAPI()
        app.include_router(router)
        app.state.backend = fake.client()
        app.state.core = make_core(fake, **core_kw)
        app.state.core.backend = app.state.backend
        return TestClient(app)

    return _make


def test_text_endpoint_persists_after_response(api):
    fake = FakeBackend(mood_routes())
    client = api(fake)
    resp = client.post("/api/v1/interact/text", json={"user_id": 3, "text": "오늘 좀 피곤해"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["mission_result"] == "success"
    assert body["oled_expression"] == "EXPR_HAPPY"

    (result,) = fake.bodies("POST", "/api/missions/11/result")
    assert result["success"] is True and result["userId"] == 3
    rows = fake.bodies("POST", "/api/conversations")
    assert [r["speaker"] for r in rows] == ["USER", "ORBIT"]
    assert {r["requestId"] for r in rows} == {body["request_id"]}


def test_text_endpoint_validates_body(api):
    client = api(FakeBackend({}))
    assert client.post("/api/v1/interact/text", json={"user_id": 3, "text": ""}).status_code == 422
    assert client.post("/api/v1/interact/text", json={"text": "안녕"}).status_code == 422


def test_voice_endpoint_requires_device_id(api):
    client = api(FakeBackend({}))
    files = {"audio": ("in.wav", io.BytesIO(b"RIFF"), "audio/wav")}
    assert client.post("/api/v1/interact/voice", files=files).status_code == 422


def test_voice_endpoint_persists_after_response(api):
    fake = FakeBackend(device_routes(FAKE_MISSION))
    client = api(fake, text="밖에 비가 와")
    files = {"audio": ("in.wav", io.BytesIO(b"RIFF"), "audio/wav")}
    resp = client.post(
        "/api/v1/interact/voice", files=files,
        data={"device_id": "ORBIT-001", "lux": "80", "request_id": "hw-1"},
    )

    assert resp.status_code == 200
    assert resp.json()["request_id"] == "hw-1"
    assert fake.called("POST", "/api/missions/12/result")
    rows = fake.bodies("POST", "/api/conversations")
    assert [r["channel"] for r in rows] == ["VOICE", "VOICE"]
    assert all(r["requestId"] == "hw-1" for r in rows)
