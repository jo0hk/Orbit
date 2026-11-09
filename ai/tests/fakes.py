"""테스트용 가짜 백엔드·모델.

백엔드 응답 JSON 형식은 backend/ 의 DTO(DeviceResponse, CharacterStatus,
MissionResponse, ConversationResponse)를 그대로 옮겼습니다. 백엔드 DTO가
바뀌면 여기 FAKE_* 값부터 고치세요.
"""

from __future__ import annotations

import json

import httpx

from app.core.backend_client import BackendClient
from app.schemas import Emotion, InteractResponse, Led, Vibe

FAKE_DEVICE = {"id": 1, "deviceId": "ORBIT-001", "charId": 7, "userId": 3}
FAKE_CHARACTER = {
    "charId": 7, "userId": 3, "fuelGauge": 45, "closeness": 0,
    "currentStage": 2, "emotionStatus": "happy", "lastActionAt": None, "intimacy": 10,
}
FAKE_MISSION = {
    "missionId": 12, "stage": 2, "title": "창밖 날씨를 보고 오빗에게 음성으로 보고하기",
    "description": "", "missionType": "WEATHER_VOICE", "status": "IN_PROGRESS",
    "assignedDate": "2026-11-09", "completedAt": None,
}
FAKE_MOOD_MISSION = {
    **FAKE_MISSION, "missionId": 11, "stage": 1,
    "title": "앱 대화창에 오늘 기분 단어로 입력하기", "missionType": "EMOTION_TEXT",
}
FAKE_RECENT = [
    {"id": 1, "userId": 3, "speaker": "USER", "message": "오늘 좀 피곤해",
     "createdAt": "2026-11-09T10:00:00", "emotion": "sad", "stage": 2,
     "channel": "VOICE", "requestId": "r1"},
    {"id": 2, "userId": 3, "speaker": "ORBIT", "message": "치직- 쉬어 가셔도 좋습니다. 오버",
     "createdAt": "2026-11-09T10:00:01", "emotion": None, "stage": 2,
     "channel": "VOICE", "requestId": "r1"},
]


def ok(body) -> httpx.Response:
    return httpx.Response(200, json=body)


class FakeBackend:
    """경로별 응답을 정하고, 들어온 요청을 기록합니다. 없는 경로는 404."""

    def __init__(self, routes: dict[tuple[str, str], httpx.Response | Exception]):
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = (request.method, request.url.path)
        if key not in self.routes:
            return httpx.Response(404, json={"message": "not found"})
        result = self.routes[key]
        if isinstance(result, Exception):
            raise result
        return result

    def client(self) -> BackendClient:
        return BackendClient("http://backend.test", transport=httpx.MockTransport(self))

    def bodies(self, method: str, path: str) -> list[dict]:
        return [
            json.loads(r.content)
            for r in self.requests
            if r.method == method and r.url.path == path
        ]

    def called(self, method: str, path: str) -> bool:
        return any(r.method == method and r.url.path == path for r in self.requests)

    def paths(self) -> list[tuple[str, str]]:
        return [(r.method, r.url.path) for r in self.requests]


def device_routes(mission: dict | None = FAKE_MISSION) -> dict:
    """ORBIT-001 → user 3 / char 7, 오늘 미션은 mission."""
    routes = {
        ("GET", "/api/devices/ORBIT-001"): ok(FAKE_DEVICE),
        ("GET", "/api/character/7"): ok(FAKE_CHARACTER),
        ("POST", "/api/conversations"): ok({}),
    }
    if mission is not None:
        routes[("GET", "/api/missions/current")] = ok(mission)
        routes[("POST", f"/api/missions/{mission['missionId']}/result")] = ok(mission)
    return routes


# ─── 가짜 모델 ───────────────────────────────────────────────
class FakeSTT:
    def __init__(self, text: str, confidence: float | None = 0.9):
        self.text, self.confidence = text, confidence

    def transcribe(self, audio_path: str):
        return self.text, self.confidence


class FakeEmotion:
    def __init__(self, emotion: Emotion = Emotion.NEUTRAL, confidence: float = 0.8):
        self.emotion, self.confidence = emotion, confidence

    def analyze(self, text: str, audio_path: str):
        return self.emotion, self.confidence


class FakeLLM:
    """사용자 감정 매핑 그대로의 신호를 돌려줍니다. 서버 덮어쓰기를 확인하려는 것."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.prompts: list[str] = []

    def generate(self, system_prompt: str, user_text: str) -> InteractResponse:
        self.prompts.append(system_prompt)
        if self.fail:
            raise RuntimeError("Gemini 503")
        return InteractResponse(
            speech="치직- 대장님, 교신 잘 받았습니다. 오버",
            led=Led.BLUE,
            vibe=Vibe.SOFT_CONTINUOUS,
        )


class FakeTTS:
    def __init__(self):
        self.calls = 0

    async def synthesize(self, text: str, out_path: str, plain: bool = False) -> str:
        self.calls += 1
        return out_path
