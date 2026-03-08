from dataclasses import dataclass

import librosa
import numpy as np


@dataclass
class AudioFeatures:
    mfcc_mean: np.ndarray
    chroma_mean: np.ndarray
    spectral_centroid_mean: float
    tempo: float
    duration: float

    def to_model_vector(self) -> np.ndarray:
        return np.concatenate(
            [
                self.mfcc_mean.astype(np.float32),
                self.chroma_mean.astype(np.float32),
                np.array([self.spectral_centroid_mean], dtype=np.float32),
            ]
        )

    def to_storage_dict(self) -> dict:
        return {
            "mfcc_mean": self.mfcc_mean.tolist(),
            "chroma_mean": self.chroma_mean.tolist(),
            "spectral_centroid_mean": float(self.spectral_centroid_mean),
        }


def extract_audio_features(file_path: str) -> AudioFeatures:
    y, sr = librosa.load(file_path, sr=22050, mono=True)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

    return AudioFeatures(
        mfcc_mean=mfcc.mean(axis=1),
        chroma_mean=chroma.mean(axis=1),
        spectral_centroid_mean=float(spectral_centroid.mean()),
        tempo=float(tempo),
        duration=float(librosa.get_duration(y=y, sr=sr)),
    )
