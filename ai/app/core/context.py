"""Context Injector — 4주차 산출물.

감정 + 환경(조도/날씨/위치) + 미션 결과를 조합해 시스템 지침을 동적으로 만듭니다.
1학기에 확립한 규칙:
  - 조도 50 lux 이하  → 태양광 충전(환기) 권유
  - 날씨 화창함        → 산책 미션 유도
2학기 추가 예정:
  - 미션 결과(success/fail/retry) 주입 (5주차)
  - GPS 거리 구간별 시나리오 (7주차)
  - 성장 레벨별 어휘/문장 길이 차등 (9주차)
"""

from __future__ import annotations

from pathlib import Path

from app.schemas import EnvContext, Emotion, MissionResult

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_persona() -> str:
    return (PROMPT_DIR / "persona.md").read_text(encoding="utf-8")


def build_system_prompt(emotion: Emotion, ctx: EnvContext) -> str:
    """페르소나 + 상황 지침을 조립합니다."""
    parts: list[str] = [load_persona()]

    parts.append(f"[현재 상황] 사용자의 감정은 '{emotion.value}'입니다.")

    if ctx.lux is not None and ctx.lux <= 50:
        parts.append("[환경] 기지 광량이 부족합니다. 태양광 충전(환기)을 권유하세요.")
    if ctx.weather:
        parts.append(f"[환경] 현재 날씨는 '{ctx.weather}'입니다.")
    if ctx.distance_m:
        parts.append(f"[탐사] 누적 이동 거리 {ctx.distance_m}m.")

    # TODO(5주차): 미션 결과별 지침을 미션 정의표의 대사와 연결
    if ctx.mission_result is not MissionResult.NONE:
        parts.append(f"[미션] '{ctx.mission_id}' 결과: {ctx.mission_result.value}.")

    return "\n".join(parts)
