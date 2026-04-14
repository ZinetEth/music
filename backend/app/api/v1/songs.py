from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.song_service import SongService

router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("")
def list_songs(limit: int = 100, db: Session = Depends(get_db)):
    songs = SongService(db).list_songs(limit=limit)
    return [
        {
            "song_id": song.navidrome_song_id,
            "title": song.title,
            "artist": song.artist,
            "genre": song.genre,
            "country": song.country,
            "qenet_mode": song.qenet_mode,
            "is_premium": song.is_premium,
        }
        for song in songs
    ]


@router.get("/premium")
def premium_song_ids(db: Session = Depends(get_db)):
    return SongService(db).list_premium_song_ids()

