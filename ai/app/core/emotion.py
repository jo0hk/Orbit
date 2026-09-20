"""멀티모달 감정 분석 (3주차 산출물).

아키텍처는 1학기 EmotionFusionModel을 그대로 옮겼습니다.
  Text : klue/roberta-small pooler output (768)
  Audio: MFCC 13 + Pitch 1 = 14차원 → MLP(64)
  Fusion: concat(832) → 256 → num_classes

⚠️ 학습 정확도 97.33%는 학습 데이터 기준입니다. 1학기 실제 테스트에서
   "피곤하다" 취지의 발화가 두 번 모두 'anger'로 분류됐습니다.
   8주차 야외 검증 전에 1주차에 한 번 더 확인해보세요.
"""

from __future__ import annotations

import logging

import numpy as np

from app.config import get_settings
from app.schemas import Emotion

logger = logging.getLogger(__name__)

AUDIO_FEATURE_DIM = 14  # MFCC 13 + Pitch 1


def _build_model_class():
    """torch 임포트를 지연시키기 위해 함수 안에서 정의합니다."""
    import torch.nn as nn
    from transformers import AutoModel

    class EmotionFusionModel(nn.Module):
        def __init__(self, num_classes: int) -> None:
            super().__init__()
            self.bert = AutoModel.from_pretrained("klue/roberta-small")
            self.audio_fc = nn.Sequential(
                nn.Linear(AUDIO_FEATURE_DIM, 64),
                nn.ReLU(),
                nn.Dropout(0.2),
            )
            self.classifier = nn.Sequential(
                nn.Linear(768 + 64, 256),
                nn.ReLU(),
                nn.Linear(256, num_classes),
            )

        def forward(self, input_ids, attention_mask, audio_feat):
            import torch

            text_out = self.bert(input_ids=input_ids, attention_mask=attention_mask)[1]
            audio_out = self.audio_fc(audio_feat)
            return self.classifier(torch.cat((text_out, audio_out), dim=1))

    return EmotionFusionModel


class EmotionEngine:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._tokenizer = None
        self._labels: list[str] = []
        self._device = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        import torch
        from transformers import AutoTokenizer

        s = self._settings
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("감정 엔진 로딩: device=%s path=%s", self._device, s.emotion_model_path)

        self._tokenizer = AutoTokenizer.from_pretrained(s.emotion_text_encoder)

        # weights_only=False: PyTorch 2.6 보안 기본값 변경 대응 (1학기 트러블슈팅)
        checkpoint = torch.load(s.emotion_model_path, map_location=self._device, weights_only=False)
        self._labels = list(checkpoint["label_encoder"])

        self._assert_labels_match_enum()

        EmotionFusionModel = _build_model_class()
        self._model = EmotionFusionModel(num_classes=len(self._labels)).to(self._device)
        self._model.load_state_dict(checkpoint["model_state_dict"])
        self._model.eval()

    def _assert_labels_match_enum(self) -> None:
        """체크포인트 라벨과 schemas.Emotion이 어긋나면 기동을 중단합니다.

        조용히 어긋나면 HW 신호가 엉뚱하게 나가는데 아무도 모릅니다.
        재학습으로 클래스를 바꾸면 여기서 먼저 걸립니다.
        """
        expected = {e.value for e in Emotion}
        actual = set(self._labels)
        if actual != expected:
            raise RuntimeError(
                f"감정 라벨 불일치. 체크포인트={sorted(actual)} / schemas.Emotion={sorted(expected)}. "
                "schemas.py의 Emotion enum을 체크포인트에 맞추세요."
            )

    def _audio_features(self, audio_path: str) -> np.ndarray:
        """MFCC 13차원 + 평균 Pitch 1차원.

        ⚠️ 1학기 코드는 bare except로 모든 실패를 삼키고 zeros(14)를 반환했습니다.
           그러면 오디오 브랜치가 통째로 무력화되는데 로그가 없어 알 수 없습니다.
           여기서는 경고를 남깁니다.
        """
        import librosa

        try:
            y, sr = librosa.load(audio_path, sr=16000)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13).mean(axis=1)
            pitches, _magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch = float(np.mean(pitches[pitches > 0])) if np.any(pitches > 0) else 0.0
            return np.concatenate([mfcc, [pitch]])
        except Exception:
            logger.warning("오디오 특징 추출 실패. 텍스트 단독으로 추론합니다: %s", audio_path, exc_info=True)
            return np.zeros(AUDIO_FEATURE_DIM)

    def analyze(self, text: str, audio_path: str) -> tuple[Emotion, float]:
        """returns (감정 라벨, 신뢰도)."""
        self._ensure_loaded()

        import torch

        inputs = self._tokenizer(
            text, return_tensors="pt", padding="max_length", truncation=True, max_length=64
        ).to(self._device)
        audio_feat = (
            torch.tensor(self._audio_features(audio_path), dtype=torch.float32)
            .unsqueeze(0)
            .to(self._device)
        )

        with torch.no_grad():
            logits = self._model(inputs["input_ids"], inputs["attention_mask"], audio_feat)
            probs = torch.softmax(logits, dim=1)
            conf, idx = torch.max(probs, dim=1)

        return Emotion(self._labels[idx.item()]), float(conf.item())
