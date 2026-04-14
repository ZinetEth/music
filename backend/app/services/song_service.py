from sqlalchemy.orm import Session

from app.repositories.song_repo import SongRepository


class SongService:
    def __init__(self, db: Session):
        self.db = db
        self.songs = SongRepository(db)

    def list_songs(self, limit: int = 100):
        return self.songs.list_catalog(limit=limit)

    def list_premium_song_ids(self) -> list[str]:
        return self.songs.list_premium_song_ids()

