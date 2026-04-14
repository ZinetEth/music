from datetime import timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models
from app.utils.helpers import utc_now


class PlaybackRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_recent_events_for_user(
        self,
        user_id: int,
        *,
        hours: int = 24 * 30,
        limit: int | None = None,
    ) -> list[models.PlaybackEvent]:
        cutoff = utc_now() - timedelta(hours=hours)
        query = (
            self.db.query(models.PlaybackEvent)
            .join(models.LibrarySong, models.LibrarySong.id == models.PlaybackEvent.song_id)
            .filter(models.PlaybackEvent.user_id == user_id)
            .filter(models.PlaybackEvent.occurred_at >= cutoff)
            .order_by(desc(models.PlaybackEvent.occurred_at))
        )
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def list_recent_events(
        self,
        *,
        hours: int = 24 * 7,
    ) -> list[models.PlaybackEvent]:
        cutoff = utc_now() - timedelta(hours=hours)
        return (
            self.db.query(models.PlaybackEvent)
            .join(models.LibrarySong, models.LibrarySong.id == models.PlaybackEvent.song_id)
            .filter(models.PlaybackEvent.occurred_at >= cutoff)
            .all()
        )

    def create(self, event: models.PlaybackEvent) -> models.PlaybackEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_active_session(
        self,
        user_id: int,
        *,
        max_idle_minutes: int = 30,
    ) -> models.ListeningSession | None:
        cutoff = utc_now() - timedelta(minutes=max_idle_minutes)
        return (
            self.db.query(models.ListeningSession)
            .filter(models.ListeningSession.user_id == user_id)
            .filter(models.ListeningSession.status == "active")
            .filter(models.ListeningSession.last_activity_at >= cutoff)
            .order_by(desc(models.ListeningSession.last_activity_at))
            .first()
        )

    def get_or_start_session(
        self,
        user_id: int,
        *,
        target_session_minutes: int = 45,
    ) -> models.ListeningSession:
        session = self.get_active_session(user_id)
        if session is not None:
            session.last_activity_at = utc_now()
            self.db.commit()
            self.db.refresh(session)
            return session

        session = models.ListeningSession(
            user_id=user_id,
            target_session_minutes=target_session_minutes,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def replace_session_recommendations(
        self,
        session_id: int,
        songs: list[tuple[str, float]],
    ) -> None:
        self.db.query(models.SessionRecommendationEvent).filter(
            models.SessionRecommendationEvent.session_id == session_id
        ).delete()

        for position, (song_id, score) in enumerate(songs, start=1):
            self.db.add(
                models.SessionRecommendationEvent(
                    session_id=session_id,
                    song_id=song_id,
                    position=position,
                    score=score,
                )
            )

        self.db.commit()
