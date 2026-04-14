from sqlalchemy.orm import Session

from app.repositories.playback_repo import PlaybackRepository
from app.repositories.song_repo import SongRepository
from app.repositories.user_repo import UserRepository


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.songs = SongRepository(db)
        self.playback = PlaybackRepository(db)
