"""멀티모달 감정 분석 (3주차 산출물, Final Accuracy 97.33%).

구조: Text Branch(klue/roberta-small) + Audio Branch(MFCC+Pitch 14차원 MLP)
      → Concatenation → 5클래스 분류

⚠️ 97.33%는 학습 데이터 기준입니다. 8주차 야외 검증에서 실사용 성능을 측정하세요.
⚠️ 가중치(.pt)는 git에 없습니다. HF Hub private repo 또는 ai/models/ 에 두세요.
"""

from __future__ import annotations

from app.config import get_settings
from app.schemas import Emotion


class EmotionEngine:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # TODO(1주차): Colab의 MultimodalFusionNet 정의 + 가중치 로딩을 옮기세요.
        #
        # import torch
        # from transformers import AutoTokenizer
        #
        # self._tokenizer = AutoTokenizer.from_pretrained(self._settings.emotion_text_encoder)
        # self._model = MultimodalFusionNet(...)
        # state = torch.load(self._settings.emotion_model_path,
        #                    map_location="cpu", weights_only=False)  # PyTorch 2.6 이슈
        # self._model.load_state_dict(state)
        # self._model.eval()
        raise NotImplementedError("1주차 이식 대상: 감정 모델 로딩")

    def analyze(self, text: str, audio_path: str) -> tuple[Emotion, float]:
        """returns (감정 라벨, 신뢰도)."""
        self._ensure_loaded()
        # TODO(1주차): librosa로 MFCC+Pitch 추출 → 텍스트 임베딩과 결합 → 추론
        raise NotImplementedError
