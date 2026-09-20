"""음성 교신 엔드포인트 (5주차 FastAPI 산출물)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.schemas import EnvContext, InteractResponse

router = APIRouter(prefix="/api/v1/interact", tags=["interact"])


@router.post("/voice", response_model=InteractResponse)
async def interact_voice(
    request: Request,
    audio: UploadFile = File(..., description="사용자 발화 음성"),
    session_id: str = Form(...),
    turn_no: int = Form(0),
    lux: int | None = Form(None),
    weather: str | None = Form(None),
    mission_id: str | None = Form(None),
) -> InteractResponse:
    """음성을 받아 오빗의 응답(speech/led/vibe/oled)을 반환합니다.

    호출 주체는 백엔드(Spring Boot)입니다. 앱이 직접 호출하지 않습니다.
    ⚠️ 이 경계는 1주차 인터페이스 정의서에서 확정하세요.
    """
    core = request.app.state.core

    with tempfile.NamedTemporaryFile(suffix=Path(audio.filename or "in.wav").suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    ctx = EnvContext(lux=lux, weather=weather, mission_id=mission_id)
    return await core.interact(tmp_path, ctx)
