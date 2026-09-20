"""탐사 인증샷 칭찬 (4주차 산출물).

gemini-2.5-flash 멀티모달로 사진 속 객체를 인식하고 구체적인 찬사를 생성합니다.
1학기 실증: '벚꽃이 만개한 나무와 푸른 하늘' 인식 → "바깥 정찰 미션을 멋지게 완수하셨군요!"

2학기 확장:
  - 7주차: GPS 이동 거리 / 날씨와 결합
  - 9주차: 반복 칭찬 방지 (최근 사용 문형 회피)
"""

from __future__ import annotations


class ExplorationVision:
    def describe_and_praise(self, image_path: str, distance_m: int | None = None) -> str:
        # TODO(1주차): Colab의 비전 호출 셀을 옮기세요.
        raise NotImplementedError
