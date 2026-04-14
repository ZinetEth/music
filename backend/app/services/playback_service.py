from sqlalchemy.orm import Session

from app import models, schemas
from app.repositories.playback_repo import PlaybackRepository
from app.repositories.song_repo import SongRepository
from app.repositories.user_repo import UserRepository
from app.services import crud


class PlaybackService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.songs = SongRepository(db)
        self.playback = PlaybackRepository(db)

    def record_playback(self, payload: schemas.PlaybackEventIn) -> schemas.PlaybackEventResponse:
        user = self.users.get_by_id(payload.user_id)
        if not user:
            raise ValueError("user_not_found")

        song = crud.get_or_create_song_from_event(self.db, payload)
        event = models.PlaybackEvent(
            user_id=payload.user_id,
            song_id=song.id,
            location=payload.location,
            completed_ratio=payload.completed_ratio,
            played_seconds=payload.played_seconds,
            is_looped=payload.is_looped,
            skipped=payload.skipped,
            weight=crud._engagement_weight(payload),
        )
        self.playback.create(event)

        song.play_count_7d += 1
        if payload.completed_ratio >= 0.85:
            song.like_count_7d += 1
        if payload.skipped:
            total = max(song.play_count_7d, 1)
            skipped_events = (
                self.db.query(models.PlaybackEvent)
                .filter(models.PlaybackEvent.song_id == song.id, models.PlaybackEvent.skipped.is_(True))
                .count()
            )
            song.skip_rate = round((skipped_events + 1) / total, 4)

        self.db.commit()
        self.db.refresh(song)

        vector = crud.refresh_user_taste_vector(self.db, payload.user_id)
        return schemas.PlaybackEventResponse(
            recorded=True,
            user_id=payload.user_id,
            song_id=payload.song_id,
            updated_taste_vector=crud._taste_vector_schema(vector),
        )
