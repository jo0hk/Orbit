"""텍스트 → 무전 톤 음성.

파이프라인: edge-tts(ko-KR-InJoonNeural) → pydub low_pass_filter
            → numpy 화이트 노이즈("치칙-") 합성

⚠️ pydub은 ffmpeg 바이너리가 필요합니다. 서버 이식 시 설치 확인하세요.
   1학기에 gTTS는 click/typer 의존성 충돌로 폐기했습니다. 되돌리지 마세요.
"""

from __future__ import annotations

from app.config import get_settings


class RadioTTS:
    def __init__(self) -> None:
        self._settings = get_settings()

    async def synthesize(self, text: str, out_path: str) -> str:
        """returns 생성된 음성 파일 경로."""
        # TODO(1주차): Colab의 edge-tts 비동기 호출 + 오디오 후처리 셀을 옮기세요.
        #   nest_asyncio 패치는 Colab 전용이므로 서버에서는 제거합니다.
        raise NotImplementedError("1주차 이식 대상: edge-tts + 무전 노이즈 합성")
