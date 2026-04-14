from collections.abc import Iterable

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app import models


class SongRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_catalog(self, limit: int = 500) -> list[models.LibrarySong]:
        return (
            self.db.query(models.LibrarySong)
            .order_by(desc(models.LibrarySong.play_count_7d), desc(models.LibrarySong.like_count_7d))
            .limit(limit)
            .all()
        )

    def list_unheard_for_user(self, user_id: int, limit: int = 500) -> list[models.LibrarySong]:
        heard_subquery = select(models.PlaybackEvent.song_id).filter(
            models.PlaybackEvent.user_id == user_id
        )
        return (
            self.db.query(models.LibrarySong)
            .filter(~models.LibrarySong.id.in_(heard_subquery))
            .order_by(desc(models.LibrarySong.play_count_7d), desc(models.LibrarySong.like_count_7d))
            .limit(limit)
            .all()
        )

    def list_recent_releases(self, limit: int = 100) -> list[models.LibrarySong]:
        return (
            self.db.query(models.LibrarySong)
            .filter(models.LibrarySong.release_date.isnot(None))
            .order_by(desc(models.LibrarySong.release_date))
            .limit(limit)
            .all()
        )

    def list_premium_song_ids(self) -> list[str]:
        rows = (
            self.db.query(models.PremiumContent.navidrome_song_id)
            .filter(models.PremiumContent.requires_subscription.is_(True))
            .all()
        )
        return [song_id for (song_id,) in rows]

    def get_by_navidrome_id(self, navidrome_song_id: str) -> models.LibrarySong | None:
        return (
            self.db.query(models.LibrarySong)
            .filter(models.LibrarySong.navidrome_song_id == navidrome_song_id)
            .first()
        )

    def list_playlist_signals(self) -> dict[str, models.PlaylistSocialSignal]:
        return {
            signal.playlist_id: signal
            for signal in self.db.query(models.PlaylistSocialSignal).all()
        }

    def list_playlist_signals_by_ids(
        self,
        playlist_ids: Iterable[str],
    ) -> dict[str, models.PlaylistSocialSignal]:
        ids = [playlist_id for playlist_id in playlist_ids if playlist_id]
        if not ids:
            return {}
        return {
            signal.playlist_id: signal
            for signal in self.db.query(models.PlaylistSocialSignal)
            .filter(models.PlaylistSocialSignal.playlist_id.in_(ids))
            .all()
        }

    def list_active_holiday_rules(self) -> list[models.HolidayRule]:
        return (
            self.db.query(models.HolidayRule)
            .filter(models.HolidayRule.is_active.is_(True))
            .order_by(models.HolidayRule.eth_month.asc(), models.HolidayRule.eth_day.asc())
            .all()
        )
