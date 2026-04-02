import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import schemas
from app.core.settings import get_settings
from app.db import get_db
from app.models import MusicMetadata

router = APIRouter(tags=["audio-analysis"])
classifier = None
settings = get_settings()

SUPPORTED_EXTENSIONS = {".mp3", ".wav"}


def get_audio_tools():
    global classifier
    try:
        from audio.classifier import QenetClassifier
        from audio.features import extract_audio_features
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Audio analysis dependencies are not installed. "
                f"Missing module: {exc.name}"
            ),
        ) from exc

    if classifier is None:
        classifier = QenetClassifier()

    return extract_audio_features, classifier


@router.post("/analyze-audio", response_model=schemas.AudioAnalysisResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    artist: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    extract_audio_features, active_classifier = get_audio_tools()
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .mp3 and .wav files are supported",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        temp_path = temp_file.name
        content = await file.read()
        if len(content) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded file is too large",
            )
        temp_file.write(content)

    try:
        features = extract_audio_features(temp_path)
        qenet_mode = active_classifier.predict(
            features.to_model_vector(), tempo=features.tempo
        )

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
