"""Orbit AI Server 엔트리포인트.

로컬 실행:
    cd ai
    uvicorn app.main:app --reload --port 8000

백엔드(Spring Boot)와는 별도 프로세스입니다. PyTorch가 Python 런타임을
요구하므로 한 서버에 합칠 수 없고, HTTP로 통신합니다.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.interact import router as interact_router
from app.core.pipeline import OrbitCore


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 모델 로딩은 기동 시 1회. 요청마다 로드하면 레이턴시가 무너집니다.
    core = OrbitCore()
    app.state.core = core
    # 모델을 미리 올려둡니다. 실패해도 기동은 계속하되 로그를 남깁니다.
    try:
        core.warmup()
    except Exception:
        logging.getLogger(__name__).warning("모델 예열 실패. 첫 요청에서 재시도합니다.", exc_info=True)
    yield


app = FastAPI(title="Orbit AI Server", version="0.1.0", lifespan=lifespan)
app.include_router(interact_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
