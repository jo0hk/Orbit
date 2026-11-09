"""한 턴의 미션 판정과 기록.

흐름: docs/mission-context-injection.md 2-1절
  1. 고위험 발화면 판정하지 않음 (결과 API도 호출하지 않음)
  2. 오늘 미션이 IN_PROGRESS + 활성 미션 + 입력 채널 일치일 때만 판정
  3. 거부 → DEFERRED, 아니면 규칙 판정 → SUCCESS / RETRY
  4. (응답 후 백그라운드) 결과 API 호출 · 대화 저장

판정 함수는 순수 함수라 모델·백엔드 없이 테스트할 수 있습니다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.backend_client import BackendClient, BackendContext
from app.core.mission_judge import Judgement, judge_mood, judge_weather
from app.missions import (
    BY_TYPE,
    SIGNAL_DEFERRED,
    SIGNAL_SUCCESS,
    SIGNAL_TIMEOUT,
    Channel,
    HwSignal,
    Mission,
    MissionType,
)
from app.schemas import CommonEmotion, MissionResult, WeatherCategory

logger = logging.getLogger(__name__)

# 미션 반응 턴의 HW 신호 (docs/mission-context-injection.md 1절)
MISSION_SIGNAL: dict[MissionResult, HwSignal] = {
    MissionResult.SUCCESS: SIGNAL_SUCCESS,
    MissionResult.RETRY: SIGNAL_TIMEOUT,
    MissionResult.DEFERRED: SIGNAL_DEFERRED,
}


@dataclass(frozen=True)
class MissionTurn:
    """이번 턴에 판정한 미션."""

    mission_id: int
    mission: Mission
    judgement: Judgement


def _weather_category(raw: str | None) -> WeatherCategory | None:
    if not raw:
        return None
    try:
        return WeatherCategory(raw.upper())
    except ValueError:
        return None


def judge_turn(
    bctx: BackendContext,
    channel: Channel,
    user_text: str,
    stt_confidence: float | None,
    *,
    high_risk: bool,
) -> MissionTurn | None:
    """이번 발화가 오늘 미션 수행이면 판정하고, 아니면 None."""
    if high_risk:
        return None
    today = bctx.mission
    if today is None or not today.in_progress:
        return None  # 미션 없음, 또는 이미 완료 (칭찬 중복 방지)

    mission = BY_TYPE.get(today.mission_type)
    if mission is None or not mission.active or mission.channel is not channel:
        return None  # 사진형 미션(비활성), 채널 불일치

    if today.mission_type is MissionType.EMOTION_TEXT:
        judgement = judge_mood(user_text)
    elif today.mission_type is MissionType.WEATHER_VOICE:
        judgement = judge_weather(user_text, stt_confidence, _weather_category(bctx.weather))
    else:
        return None

    if judgement is None:
        return None  # STT 신뢰도 미달 → 판정 없이 되묻기
    return MissionTurn(today.mission_id, mission, judgement)


@dataclass
class TurnRecord:
    """응답을 내보낸 뒤 백엔드에 남길 것."""

    user_id: int | None
    request_id: str
    channel: Channel
    user_text: str
    orbit_speech: str
    emotion: CommonEmotion | None
    stage: int | None
    mission_turn: MissionTurn | None = None


async def persist_turn(backend: BackendClient | None, record: TurnRecord) -> None:
    """미션 결과 전송과 대화 저장. 응답 후 백그라운드에서 부릅니다.

    결과를 먼저 보냅니다. 결과 전송이 실패해도 다음 턴에 백엔드가 여전히
    IN_PROGRESS 를 주면 다시 판정됩니다(docs/mission-context-injection.md 2-1절).
    """
    if backend is None:
        return
    if record.user_id is None:
        logger.warning("사용자를 알 수 없어 기록하지 않음: requestId=%s", record.request_id)
        return

    turn = record.mission_turn
    if turn is not None:
        await backend.report_mission_result(
            mission_id=turn.mission_id,
            user_id=record.user_id,
            judgement=turn.judgement,
        )

    await backend.save_turn(
        user_id=record.user_id,
        request_id=record.request_id,
        user_text=record.user_text,
        orbit_speech=record.orbit_speech,
        emotion=record.emotion,
        stage=record.stage,
        channel=record.channel,
    )
