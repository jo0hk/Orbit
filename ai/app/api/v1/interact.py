"""교신 엔드포인트.

호출 경로 (docs/interface-spec-v1.md 1절, 09-17 회의 결정):
  - 키링 음성 → POST /api/v1/interact/voice  (키링이 직접 호출)
  - 앱 텍스트 → POST /api/v1/interact/text   (앱이 직접 호출)

사용자·단계·오늘 미션은 AI 서버가 백엔드에서 조회합니다. 미션 결과 전송과
대화 저장은 응답을 내보낸 뒤 백그라운드에서 합니다. 백엔드가 응답하지 않아도
사용자 응답은 정상으로 나갑니다.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile

from app.core.turn import persist_turn
from app.schemas import InteractResponse, TextInteractRequest

router = APIRouter(prefix="/api/v1/interact", tags=["interact"])


@router.post("/voice", response_model=InteractResponse)
async def interact_voice(
    request: Request,
    background: BackgroundTasks,
    audio: UploadFile = File(..., description="사용자 발화 음성. 16kHz mono WAV 권장"),
    device_id: str = Form(..., description="키링 ID (예: ORBIT-001)"),
    lux: int | None = Form(None, description="조도"),
    request_id: str | None = Form(None, description="중복 저장 방지용. 없으면 서버가 발급"),
) -> InteractResponse:
    """음성을 받아 오빗의 응답(speech/audio_url/led/vibe/oled)을 반환합니다."""
    core = request.app.state.core

    suffix = Path(audio.filename or "in.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        outcome = await core.interact_voice(
            tmp_path, device_id=device_id, lux=lux, request_id=request_id
        )
    finally:
        # 사용자 음성 원본은 처리 후 남기지 않습니다.
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    background.add_task(persist_turn, getattr(request.app.state, "backend", None), outcome.record)
    return outcome.response


@router.post("/text", response_model=InteractResponse)
async def interact_text(
    body: TextInteractRequest,
    request: Request,
    background: BackgroundTasks,
) -> InteractResponse:
    """앱 텍스트 교신. 1단계 미션(기분 텍스트)이 이 경로로 들어옵니다. 음성 합성은 하지 않습니다."""
    core = request.app.state.core
    outcome = await core.interact_text(
        body.text, user_id=body.user_id, request_id=body.request_id
    )
    background.add_task(persist_turn, getattr(request.app.state, "backend", None), outcome.record)
    return outcome.response
