"""Context Injector — 4주차 산출물.

1학기 ContextInjector.inject()를 옮긴 것입니다. 정적인 페르소나는
prompts/persona.md로 분리하고, 상황에 따라 달라지는 부분만 여기서 조립합니다.

1학기에 확립된 규칙(유지):
  - 조도 50 lux 이하  → 태양광 충전(환기) 권유 한 문장
  - 날씨 화창 + sad   → 산책 미션 유도
  - speech는 45자 이내 (max_output_tokens 대신 프롬프트로 제어)
2학기 추가:
  - 미션 결과 주입 (5주차)
  - GPS 거리 구간 (7주차)
  - 성장 레벨별 어휘 차등 (9주차)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.schemas import Emotion, EnvContext, MissionResult

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache
def load_persona() -> str:
    return (PROMPT_DIR / "persona.md").read_text(encoding="utf-8")


def build_system_prompt(emotion: Emotion, ctx: EnvContext) -> str:
    parts: list[str] = [load_persona()]

    parts.append("\n[현재 대장님의 우주 기지(환경) 정보]")
    parts.append(f"- 생체 감정 신호: {emotion.value}")
    if ctx.location_coarse:
        parts.append(f"- 현재 위치(GPS 기지): {ctx.location_coarse}")
    if ctx.weather:
        parts.append(f"- 외기 날씨 상태: {ctx.weather}")
    if ctx.lux is not None:
        parts.append(f"- 기지 내 조도: {ctx.lux} lux")

    parts.append("\n[환경별 컨텍스트 제어 수칙]")
    if ctx.lux is not None and ctx.lux <= 50:
        parts.append(
            "1. 조도 제어: 기지가 어두우니 창문을 열어 태양광을 충전하라는 취지의 문장을 "
            "딱 하나만 짧게 붙이세요. 길게 늘이지 마세요."
        )
    if ctx.weather and emotion is Emotion.SAD:
        parts.append(
            "2. 날씨 제어: 날씨가 좋으니 가벼운 산책 미션을 권장한다는 취지로 아주 간결하게 "
            "바깥 활동을 유도하세요. 강요하지 마세요."
        )

    # TODO(5주차): 미션 정의표의 성공/실패/재시도 대사와 연결
    if ctx.mission_result is not MissionResult.NONE:
        parts.append(f"\n[미션] '{ctx.mission_id}' 결과: {ctx.mission_result.value}.")
    # TODO(7주차): 거리 구간별 시나리오
    if ctx.distance_m:
        parts.append(f"[탐사] 누적 이동 거리 {ctx.distance_m}m.")

    return "\n".join(parts)
