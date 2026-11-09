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

from app.missions import BY_TYPE, Mission, MissionType, ReasonCode
from app.schemas import Emotion, EnvContext, MissionResult

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"

# docs/mission-context-injection.md 3-1절
RESULT_LABEL = {
    MissionResult.SUCCESS: "성공",
    MissionResult.RETRY: "조건 미달(재시도 가능)",
    MissionResult.DEFERRED: "보류",
}


@lru_cache
def load_persona() -> str:
    return (PROMPT_DIR / "persona.md").read_text(encoding="utf-8")


def _mission_of(ctx: EnvContext) -> Mission | None:
    """미션 블록을 넣을 턴이면 미션 정의를, 아니면 None."""
    if ctx.mission_result is MissionResult.NONE or not ctx.mission_type:
        return None
    try:
        return BY_TYPE.get(MissionType(ctx.mission_type))
    except ValueError:
        return None


def build_mission_block(mission: Mission, ctx: EnvContext, emotion: Emotion) -> str:
    """결과별 미션 반응 수칙 블록 (docs/mission-context-injection.md 3-2·3-3절).

    블록당 공백 포함 450자 이내가 목표입니다. 1학기에 프롬프트가 비대해져
    503을 맞은 이력이 있습니다.
    """
    result = ctx.mission_result
    if result is MissionResult.SUCCESS:
        lines = [
            "[미션 반응 수칙 — 임무 성공]",
            f"- 임무: {mission.title} ({mission.stage.value}단계)",
            f"- 대장님이 방금 한 일: {mission.achievement}",
            "1. 이번 응답의 주인공은 성공 축하다. 우주 수준으로 과장하되,",
            "   길이가 아니라 단어의 스케일(은하·본부·초신성·기록)로 과장하라.",
            "2. 대장님이 한 행동을 구체적으로 한 번 짚어라.",
            "3. 45자 규칙은 예외 없이 지킨다. 느낌표는 1개까지.",
            f'4. 참고 대사(복사 금지, 변주할 것): "{mission.success[0]}" / "{mission.success[1]}"',
            "5. led는 rainbow, vibe는 strong_double.",
        ]
        # 감정 모델의 원래 라벨 기준 (3-3절). 축하는 유지하고 톤만 낮춤
        if emotion in (Emotion.SAD, Emotion.FEAR):
            lines += [
                "6. 대장님 감정이 가라앉아 있다. 과장 톤을 한 단계 낮춰 따뜻하게 축하하라.",
                "   축하 자체는 생략하지 마라.",
            ]
    elif result is MissionResult.RETRY:
        shortfall = None
        if ctx.mission_reason:
            try:
                shortfall = mission.shortfalls.get(ReasonCode(ctx.mission_reason))
            except ValueError:
                shortfall = None
        lines = [
            "[미션 반응 수칙 — 조건 미달]",
            f"- 임무: {mission.title}",
            f"- 부족했던 것: {shortfall or '수신 신호가 약함'}",
            '1. "실패"라는 단어를 쓰지 마라. 부족한 것은 수신 신호이지 대장님이 아니다.',
            "2. 무엇이 부족했는지 한 구절로 짚고, 다시 할지는 대장님이 고르게 하라.",
            "3. 재촉하는 표현(빨리, 꼭, 반드시, 다시 해야)을 쓰지 마라.",
            f'4. 참고 대사(복사 금지): "{mission.retry[0]}" / "{mission.retry[1]}"',
        ]
    else:  # DEFERRED
        lines = [
            "[미션 반응 수칙 — 임무 보류]",
            f"- 임무: {mission.title}",
            '1. 보류를 담담히 접수하라. "실패", "아쉽다"를 쓰지 마라.',
            "2. 이 임무를 다시 권하지 마라. 쉬어도 된다는 뜻만 전하라.",
            "3. led는 blue, vibe는 soft_continuous.",
        ]
    return "\n".join(lines)


def build_system_prompt(emotion: Emotion, ctx: EnvContext) -> str:
    parts: list[str] = [load_persona()]
    mission = _mission_of(ctx)

    parts.append("\n[현재 대장님의 우주 기지(환경) 정보]")
    parts.append(f"- 생체 감정 신호: {emotion.value}")
    if ctx.location_coarse:
        parts.append(f"- 현재 위치(GPS 기지): {ctx.location_coarse}")
    if ctx.weather:
        parts.append(f"- 외기 날씨 상태: {ctx.weather}")
    if ctx.lux is not None:
        parts.append(f"- 기지 내 조도: {ctx.lux} lux")
    if mission is not None:
        parts.append(f"- 미션 교신: {mission.title} → {RESULT_LABEL[ctx.mission_result]}")

    # 미션 반응 턴에는 환경 수칙을 끕니다. 45자 안에 지시가 겹치면 전부 흐려집니다 (3-4절).
    parts.append("\n[환경별 컨텍스트 제어 수칙]")
    if ctx.lux is not None and ctx.lux <= 50 and mission is None:
        parts.append(
            "1. 조도 제어: 기지가 어두우니 창문을 열어 태양광을 충전하라는 취지의 문장을 "
            "딱 하나만 짧게 붙이세요. 길게 늘이지 마세요."
        )
    if ctx.weather and emotion is Emotion.SAD and mission is None:
        parts.append(
            "2. 날씨 제어: 날씨가 좋으니 가벼운 산책 미션을 권장한다는 취지로 아주 간결하게 "
            "바깥 활동을 유도하세요. 강요하지 마세요."
        )

    if mission is not None:
        parts.append("\n" + build_mission_block(mission, ctx, emotion))
    # TODO(7주차): 거리 구간별 시나리오
    if ctx.distance_m:
        parts.append(f"[탐사] 누적 이동 거리 {ctx.distance_m}m.")

    return "\n".join(parts)
