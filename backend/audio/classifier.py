import os

import numpy as np

QENET_LABELS = ["Tezeta", "Bati", "Ambassel", "Anchihoye"]

try:
    import torch
except Exception:  # pragma: no cover
    torch = None


class QenetClassifier:
    """
    Wrapper around a pre-trained LSTM/CNN model.
    Expects model to output logits for 4 classes in QENET_LABELS order.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or os.getenv(
            "QENET_MODEL_PATH", "artifacts/qenet_cnn.pt"
        )
        self.model = None
        self._load_model_if_available()

    def _load_model_if_available(self):
        if torch is None:
            return
        if not os.path.exists(self.model_path):
            return
        self.model = torch.jit.load(self.model_path, map_location="cpu")
        self.model.eval()

    def predict(self, feature_vector: np.ndarray, tempo: float) -> str:
        if self.model is not None and torch is not None:
            x = torch.tensor(feature_vector, dtype=torch.float32).unsqueeze(0)
            with torch.no_grad():
                logits = self.model(x)
            predicted_idx = int(torch.argmax(logits, dim=1).item())
            return QENET_LABELS[predicted_idx]

        # Fallback heuristic for environments without model artifact.
        return self._heuristic_predict(feature_vector, tempo)

    @staticmethod
    def _heuristic_predict(feature_vector: np.ndarray, tempo: float) -> str:
        spectral_centroid_mean = float(feature_vector[-1])
        if tempo < 80:
            return "Tezeta"
        if tempo >= 130:
            return "Bati"
        if spectral_centroid_mean > 2200:
            return "Anchihoye"
        return "Ambassel"
