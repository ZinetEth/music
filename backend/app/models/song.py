from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.utils.helpers import utc_now


class PremiumContent(Base):
    __tablename__ = "premium_content"

    id = Column(Integer, primary_key=True, index=True)
    navidrome_song_id = Column(String, nullable=False, unique=True, index=True)
    requires_subscription = Column(Boolean, nullable=False, default=True)


class MusicMetadata(Base):
    __tablename__ = "music_metadata"

    id = Column(Integer, primary_key=True, index=True)
    artist = Column(String(255), nullable=True, index=True)
    genre = Column(String(100), nullable=False, default="Ethiopian Music")
    qenet_mode = Column(String(50), nullable=False, index=True)
    tempo = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    filename = Column(String(255), nullable=False)
    extracted_features = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class LibrarySong(Base):
    __tablename__ = "library_songs"

    id = Column(Integer, primary_key=True, index=True)
    navidrome_song_id = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False, index=True)
    genre = Column(String(100), nullable=False, default="Unknown")
    country = Column(String(100), nullable=True, index=True)
    language = Column(String(100), nullable=True)
    qenet_mode = Column(String(50), nullable=True, index=True)
    release_date = Column(String(20), nullable=True)
    tempo = Column(Float, nullable=False, default=0.0)
    duration = Column(Float, nullable=False, default=0.0)
    extracted_features = Column(JSON, nullable=False, default=dict)
    playlist_id = Column(String(255), nullable=True, index=True)
    play_count_7d = Column(Integer, nullable=False, default=0)
    like_count_7d = Column(Integer, nullable=False, default=0)
    skip_rate = Column(Float, nullable=False, default=0.0)
    cover_art_path = Column(String(255), nullable=True)
    stream_path = Column(String(255), nullable=True)
    is_premium = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    playback_events = relationship("PlaybackEvent", back_populates="song")


class PlaylistSocialSignal(Base):
    __tablename__ = "playlist_social_signals"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    creator_name = Column(String(255), nullable=False)
    artist_name = Column(String(255), nullable=True)
    artist_verified = Column(Boolean, nullable=False, default=False)
    save_count = Column(Integer, nullable=False, default=0)
    share_count = Column(Integer, nullable=False, default=0)
    region = Column(String(100), nullable=True, index=True)
    preview_song_id = Column(String(255), nullable=True)
    cover_art_path = Column(String(255), nullable=True)
    internal_stream_path = Column(String(255), nullable=True)
    internal_art_path = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class UserPlaylistSave(Base):
    __tablename__ = "user_playlist_saves"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    playlist_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    user = relationship("User", back_populates="playlist_saves")
