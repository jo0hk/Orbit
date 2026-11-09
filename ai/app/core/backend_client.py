"""백엔드(Spring Boot) 호출 클라이언트.

호출 경로: docs/interface-spec-v1.md 1절
  - 맥락 조회: 기기 → 사용자·캐릭터, 오늘 미션, 최근 대화
  - 대화 저장: POST /api/conversations (USER 행, ORBIT 행)
  - 미션 결과: POST /api/missions/{missionId}/result (SUCCESS·RETRY일 때만)

원칙 (09-17 회의): 백엔드가 응답하지 않아도 사용자 응답은 정상이어야 합니다.
그래서 이 클래스의 메서드는 예외를 던지지 않습니다. 실패하면 None / False /
빈 값을 돌려주고 로그만 남깁니다. 대화 원문은 로그에 남기지 않습니다.

백엔드에 Context API가 아직 없어 기존 API 여러 개를 조합합니다.
Context API가 생기면 fetch_context() 안쪽만 바꾸면 됩니다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.mission_judge import Judgement
from app.missions import Channel, MissionType
from app.schemas import CommonEmotion, MissionResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 3.0
RECENT_LIMIT = 10  # 5턴 (USER·ORBIT 2행씩). docs/conversation-log-spec.md


# ─────────────────────────────────────────────────────────────
# 백엔드 응답 모델 (camelCase → snake_case)
# ─────────────────────────────────────────────────────────────
class _BackendModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DeviceInfo(_BackendModel):
    """GET /api/devices/{deviceId} — DeviceResponse"""

    device_id: str = Field(alias="deviceId")
    user_id: int | None = Field(None, alias="userId")
    char_id: int | None = Field(None, alias="charId")


class CharacterState(_BackendModel):
    """GET /api/character/{charId} — CharacterStatus 엔티티"""

    char_id: int = Field(alias="charId")
    user_id: int | None = Field(None, alias="userId")
    stage: int | None = Field(None, alias="currentStage")
    fuel: int | None = Field(None, alias="fuelGauge")
    intimacy: int | None = None
    emotion_status: str | None = Field(None, alias="emotionStatus")


class TodayMission(_BackendModel):
    """GET /api/missions/current — MissionResponse"""

    mission_id: int = Field(alias="missionId")
    stage: int
    mission_type: MissionType = Field(alias="missionType")
    status: str | None = None  # IN_PROGRESS | COMPLETED

    @property
    def in_progress(self) -> bool:
        return self.status == "IN_PROGRESS"


class ConversationTurn(_BackendModel):
    """GET /api/conversations/{userId}/recent — ConversationResponse"""

    speaker: str  # USER | ORBIT
    message: str
    emotion: str | None = None
    stage: int | None = None
    channel: str | None = None
    created_at: str | None = Field(None, alias="createdAt")


@dataclass
class BackendContext:
    """한 턴에 필요한 백엔드 맥락. 조회에 실패한 항목은 None / 빈 리스트입니다.

    weather 는 백엔드에 아직 제공 API가 없어 항상 None 입니다
    (docs/stage-mission-judgement.md 4절 2번).
    """

    user_id: int | None = None
    char_id: int | None = None
    character: CharacterState | None = None
    mission: TodayMission | None = None
    recent: list[ConversationTurn] = field(default_factory=list)
    weather: str | None = None

    @property
    def stage(self) -> int | None:
        """현재 단계. 캐릭터 상태를 먼저 보고, 없으면 오늘 미션의 단계를 씁니다."""
        if self.character and self.character.stage is not None:
            return self.character.stage
        if self.mission:
            return self.mission.stage
        return None


# 백엔드 ConversationChannel enum 은 TEXT / VOICE 뿐입니다.
_CONVERSATION_CHANNELS = {Channel.TEXT, Channel.VOICE}


class BackendClient:
    """앱 기동 시 1회 만들고 재사용합니다. 종료 시 aclose()를 호출하세요."""

    def __init__(
        self,
        base_url: str,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_s,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    # ─── 내부 ─────────────────────────────────────────────
    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response | None:
        """요청을 보내고 응답을 돌려줍니다. 연결 실패·타임아웃이면 None."""
        try:
            return await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.warning("백엔드 호출 실패: %s %s (%s)", method, path, type(exc).__name__)
            return None

    @staticmethod
    def _json(resp: httpx.Response, method: str, path: str):
        try:
            return resp.json()
        except ValueError:
            logger.warning("백엔드 응답이 JSON이 아님: %s %s", method, path)
            return None

    async def _get_model(self, path: str, model: type[BaseModel], **kwargs):
        """GET 후 모델로 변환. 404·오류·형식 불일치면 None."""
        resp = await self._request("GET", path, **kwargs)
        if resp is None:
            return None
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            logger.warning("백엔드 오류 응답: GET %s → %s", path, resp.status_code)
            return None
        data = self._json(resp, "GET", path)
        if data is None:
            return None
        try:
            return model.model_validate(data)
        except ValidationError:
            logger.warning("백엔드 응답 형식 불일치: GET %s → %s", path, model.__name__)
            return None

    # ─── 조회 ─────────────────────────────────────────────
    async def get_device(self, device_id: str) -> DeviceInfo | None:
        return await self._get_model(f"/api/devices/{device_id}", DeviceInfo)

    async def get_character(self, char_id: int) -> CharacterState | None:
        return await self._get_model(f"/api/character/{char_id}", CharacterState)

    async def get_today_mission(
        self, user_id: int, *, assign_if_missing: bool = True
    ) -> TodayMission | None:
        """오늘 미션을 조회합니다.

        오늘 배정된 미션이 없으면(404) 배정 API를 부릅니다. 백엔드 배정 API는
        이미 배정된 미션이 있으면 그것을 돌려주므로 여러 번 불러도 같은 결과입니다.
        """
        mission = await self._get_model(
            "/api/missions/current", TodayMission, params={"userId": user_id}
        )
        if mission is not None or not assign_if_missing:
            return mission

        path = "/api/missions/today/assign"
        resp = await self._request("POST", path, params={"userId": user_id})
        if resp is None:
            return None
        if resp.status_code >= 400:
            logger.warning("오늘 미션 배정 실패: POST %s → %s", path, resp.status_code)
            return None
        data = self._json(resp, "POST", path)
        if data is None:
            return None
        try:
            return TodayMission.model_validate(data)
        except ValidationError:
            logger.warning("백엔드 응답 형식 불일치: POST %s → TodayMission", path)
            return None

    async def get_recent_conversations(
        self, user_id: int, limit: int = RECENT_LIMIT
    ) -> list[ConversationTurn]:
        path = f"/api/conversations/{user_id}/recent"
        resp = await self._request("GET", path, params={"limit": limit})
        if resp is None or resp.status_code == 404:
            return []
        if resp.status_code >= 400:
            logger.warning("백엔드 오류 응답: GET %s → %s", path, resp.status_code)
            return []
        data = self._json(resp, "GET", path)
        if not isinstance(data, list):
            return []
        turns: list[ConversationTurn] = []
        for item in data:
            try:
                turns.append(ConversationTurn.model_validate(item))
            except ValidationError:
                logger.warning("대화 기록 한 건의 형식이 맞지 않아 건너뜀: GET %s", path)
        return turns

    async def fetch_context(
        self,
        *,
        device_id: str | None = None,
        user_id: int | None = None,
        recent_limit: int = RECENT_LIMIT,
    ) -> BackendContext:
        """한 턴에 필요한 맥락을 모읍니다.

        키링 음성은 device_id, 앱 텍스트는 user_id로 부릅니다. 둘 다 있으면
        device_id로 찾은 사용자를 씁니다. 기기 조회에 실패하면 user_id로 진행합니다.
        recent_limit 이 0 이하면 최근 대화를 조회하지 않습니다.
        """
        ctx = BackendContext(user_id=user_id)

        if device_id:
            device = await self.get_device(device_id)
            if device is None:
                logger.warning("기기에 연결된 사용자를 찾지 못함: %s", device_id)
            else:
                ctx.user_id = device.user_id or user_id
                ctx.char_id = device.char_id

        if ctx.char_id is not None:
            ctx.character = await self.get_character(ctx.char_id)
            if ctx.user_id is None and ctx.character is not None:
                ctx.user_id = ctx.character.user_id

        if ctx.user_id is None:
            return ctx

        ctx.mission = await self.get_today_mission(ctx.user_id)
        if recent_limit > 0:
            ctx.recent = await self.get_recent_conversations(ctx.user_id, recent_limit)
        return ctx

    # ─── 기록 ─────────────────────────────────────────────
    async def save_turn(
        self,
        *,
        user_id: int,
        request_id: str,
        user_text: str,
        orbit_speech: str,
        emotion: CommonEmotion | None,
        stage: int | None,
        channel: Channel,
    ) -> bool:
        """한 턴을 USER 행·ORBIT 행 두 개로 저장합니다. 둘 다 성공하면 True.

        필드 규칙: docs/conversation-log-spec.md 3절
          - emotion 은 USER 행에만 넣습니다.
          - requestId 는 두 행이 같은 값을 씁니다. 백엔드 중복 판정이
            (requestId, speaker) 기준이기 때문입니다 (ConversationRepository).
          - 사용자 발화가 비어 있으면(STT 무음 등) USER 행은 건너뜁니다.
        """
        channel_value = channel.value if channel in _CONVERSATION_CHANNELS else None
        rows = []
        if user_text.strip():
            rows.append(
                {
                    "userId": user_id,
                    "speaker": "USER",
                    "message": user_text,
                    "emotion": emotion.value if emotion else None,
                    "stage": stage,
                    "channel": channel_value,
                    "requestId": request_id,
                }
            )
        if orbit_speech.strip():
            rows.append(
                {
                    "userId": user_id,
                    "speaker": "ORBIT",
                    "message": orbit_speech,
                    "emotion": None,
                    "stage": stage,
                    "channel": channel_value,
                    "requestId": request_id,
                }
            )

        ok = True
        path = "/api/conversations"
        for row in rows:
            resp = await self._request("POST", path, json=row)
            if resp is None:
                ok = False
            elif resp.status_code >= 400:
                logger.warning(
                    "대화 저장 실패: speaker=%s requestId=%s → %s",
                    row["speaker"], request_id, resp.status_code,
                )
                ok = False
        return ok

    async def report_mission_result(
        self,
        *,
        mission_id: int,
        user_id: int,
        judgement: Judgement,
        detail: str | None = None,
    ) -> bool | None:
        """미션 판정 결과를 백엔드에 보냅니다.

        반환값: 보냈으면 True, 보내려다 실패하면 False,
        보낼 대상이 아니면(DEFERRED 거부, NONE) None.

        - SUCCESS → success:true, RETRY → success:false (실패가 아니라 "아직")
        - DEFERRED(거부)는 결과 API를 호출하지 않습니다 (docs/stage-mission-judgement.md 3절).
        - reason 은 "코드: 설명" 형식. 로그·회귀 테스트용이며 사용자에게 보이지 않습니다.
        """
        if judgement.result is MissionResult.SUCCESS:
            success = True
        elif judgement.result is MissionResult.RETRY:
            success = False
        else:
            return None

        reason = judgement.reason.value if judgement.reason else None
        if reason and detail:
            reason = f"{reason}: {detail}"

        path = f"/api/missions/{mission_id}/result"
        body = {
            "userId": user_id,
            "success": success,
            "confidence": judgement.confidence,
            "reason": reason,
        }
        resp = await self._request("POST", path, json=body)
        if resp is None:
            return False
        if resp.status_code == 409:
            # 이미 완료된 미션이거나 캐릭터 단계와 미션 단계가 다름
            logger.info("미션 결과 반영 안 됨(409): missionId=%s", mission_id)
            return False
        if resp.status_code >= 400:
            logger.warning("미션 결과 전송 실패: POST %s → %s", path, resp.status_code)
            return False
        return True
