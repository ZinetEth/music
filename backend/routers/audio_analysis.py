import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import schemas
from audio.classifier import QenetClassifier
from audio.features import extract_audio_features
from database import get_db
from models import MusicMetadata

router = APIRouter(tags=["audio-analysis"])
classifier = QenetClassifier()

SUPPORTED_EXTENSIONS = {".mp3", ".wav"}


@router.post("/analyze-audio", response_model=schemas.AudioAnalysisResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    artist: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .mp3 and .wav files are supported",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        temp_path = temp_file.name
        content = await file.read()
        temp_file.write(content)

    try:
        features = extract_audio_features(temp_path)
        qenet_mode = classifier.predict(features.to_model_vector(), tempo=features.tempo)

        # Save extracted features for future recommendation ranking/embeddings.
        # Example downstream use: blend this vector with user listening history.
        metadata = MusicMetadata(
            artist=artist,
            genre="Ethiopian Music",
            qenet_mode=qenet_mode,
            tempo=features.tempo,
            duration=features.duration,
            filename=file.filename or "unknown",
            extracted_features=features.to_storage_dict(),
        )
        db.add(metadata)
        db.commit()

        return {
            "Genre": "Ethiopian Music",
            "Qenet Mode": qenet_mode,
            "Tempo": round(features.tempo, 2),
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
