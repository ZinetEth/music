"""
Music domain models.

This module defines all music-related database models including
songs, playlists, metadata, and social features.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Create separate base for music domain to avoid conflicts
MusicBase = declarative_base()
utc_now = lambda: datetime.now(UTC)


class Song(MusicBase):
    """
    Song model for music metadata and content.
    
    Completely isolated from payment logic - no payment fields.
    """
    __tablename__ = "music_songs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic metadata
    title = Column(String(255), nullable=False, index=True)
    artist = Column(String(255), nullable=False, index=True)
    album = Column(String(255), nullable=True, index=True)
    genre = Column(String(100), nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # File information
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    format = Column(String(10), nullable=True)  # mp3, flac, etc.
    bitrate = Column(Integer, nullable=True)
    
    # Metadata
    year = Column(Integer, nullable=True)
    track_number = Column(Integer, nullable=True)
    lyrics = Column(Text, nullable=True)
    
    # External IDs
    external_id = Column(String(255), nullable=True, index=True)  # Navidrome ID, etc.
    isrc = Column(String(12), nullable=True, index=True)  # International Standard Recording Code
    
    # Status and flags
    is_active = Column(Boolean, nullable=False, default=True)
    is_explicit = Column(Boolean, nullable=False, default=False)
    is_public = Column(Boolean, nullable=False, default=True)
    
    # Ownership
    uploader_id = Column(String(255), nullable=False, index=True)  # User who uploaded
    owner_id = Column(String(255), nullable=False, index=True)    # Rights holder
    
    # Metadata for search and recommendations
    song_metadata = Column(JSON, nullable=True, default=dict)
    tags = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    last_played_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    playlist_songs = relationship("PlaylistSong", back_populates="song")
    playback_events = relationship("PlaybackEvent", back_populates="song")
    social_signals = relationship("SongSocialSignal", back_populates="song")

    # Constraints
    __table_args__ = (
        UniqueConstraint('external_id', 'owner_id', name='unique_song_external_id'),
    )


class Playlist(MusicBase):
    """
    Playlist model for user-created collections.
    
    Completely isolated from payment logic - no payment fields.
    """
    __tablename__ = "music_playlists"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Ownership and access
    owner_id = Column(String(255), nullable=False, index=True)
    is_public = Column(Boolean, nullable=False, default=True)
    is_collaborative = Column(Boolean, nullable=False, default=False)
    
    # Content metadata
    song_count = Column(Integer, nullable=False, default=0)
    total_duration_seconds = Column(Integer, nullable=False, default=0)
    cover_image_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # External integrations
    external_id = Column(String(255), nullable=True, index=True)  # Navidrome ID, etc.
    
    # Metadata
    playlist_metadata = Column(JSON, nullable=True, default=dict)
    tags = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    songs = relationship("PlaylistSong", back_populates="playlist", order_by="PlaylistSong.position")
    social_signals = relationship("PlaylistSocialSignal", back_populates="playlist")
    marketplace_listings = relationship("MarketplaceListing", back_populates="playlist")


class PlaylistSong(MusicBase):
    """
    Junction table for playlist-song relationships.
    """
    __tablename__ = "playlist_songs"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    
    # Position and ordering
    position = Column(Integer, nullable=False)
    
    # Metadata
    added_by = Column(String(255), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    
    # Additional metadata
    song_metadata = Column(JSON, nullable=True, default=dict)

    # Relationships
    playlist = relationship("Playlist", back_populates="songs")
    song = relationship("Song", back_populates="playlist_songs")

    # Constraints
    __table_args__ = (
        UniqueConstraint('playlist_id', 'song_id', name='unique_playlist_song'),
        UniqueConstraint('playlist_id', 'position', name='unique_playlist_position'),
    )


class PlaybackEvent(MusicBase):
    """
    Playback event tracking for analytics and recommendations.
    """
    __tablename__ = "playback_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # Event details
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Playback information
    played_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    duration_played_seconds = Column(Integer, nullable=True)
    completed = Column(Boolean, nullable=False, default=False)
    
    # Context
    source = Column(String(50), nullable=True)  # playlist, album, search, etc.
    source_id = Column(String(255), nullable=True, index=True)
    device_type = Column(String(50), nullable=True)
    
    # Location
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Metadata
    event_metadata = Column(JSON, nullable=True, default=dict)

    # Relationships
    song = relationship("Song", back_populates="playback_events")


class SongSocialSignal(MusicBase):
    """
    Social signals for songs (likes, shares, etc.).
    """
    __tablename__ = "song_social_signals"

    id = Column(Integer, primary_key=True, index=True)
    
    # Signal details
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)  # like, share, add_to_playlist
    signal_value = Column(Float, nullable=False, default=1.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    
    # Metadata
    event_metadata = Column(JSON, nullable=True, default=dict)

    # Relationships
    song = relationship("Song", back_populates="social_signals")

    # Constraints
    __table_args__ = (
        UniqueConstraint('song_id', 'user_id', 'signal_type', name='unique_song_social_signal'),
    )


class PlaylistSocialSignal(MusicBase):
    """
    Social signals for playlists.
    """
    __tablename__ = "playlist_social_signals"

    id = Column(Integer, primary_key=True, index=True)
    
    # Signal details
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)  # like, share, follow
    signal_value = Column(Float, nullable=False, default=1.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    
    # Metadata
    event_metadata = Column(JSON, nullable=True, default=dict)

    # Relationships
    playlist = relationship("Playlist", back_populates="social_signals")

    # Constraints
    __table_args__ = (
        UniqueConstraint('playlist_id', 'user_id', 'signal_type', name='unique_playlist_social_signal'),
    )


class MarketplaceListing(MusicBase):
    """
    Marketplace listings for playlists and songs.
    
    Completely isolated from payment logic - no payment fields.
    Payment integration happens through payment domain.
    """
    __tablename__ = "marketplace_listings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Item details
    item_type = Column(String(50), nullable=False, index=True)  # playlist, song
    item_id = Column(Integer, nullable=False, index=True)
    
    # Pricing
    price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="ETB")
    
    # Seller information
    seller_id = Column(String(255), nullable=False, index=True)
    
    # Status
    status = Column(String(20), nullable=False, default="active")  # active, sold, removed
    is_featured = Column(Boolean, nullable=False, default=False)
    
    # Sales tracking
    sales_count = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    listing_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    playlist = relationship("Playlist", back_populates="marketplace_listings")

    # Constraints
    __table_args__ = (
        UniqueConstraint('item_type', 'item_id', 'seller_id', name='unique_marketplace_listing'),
    )


class Purchase(MusicBase):
    """
    Purchase records for marketplace items.
    
    Links to payment domain through payment_intent_id.
    """
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    
    # Purchase details
    buyer_id = Column(String(255), nullable=False, index=True)
    seller_id = Column(String(255), nullable=False, index=True)
    item_type = Column(String(50), nullable=False, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    
    # Payment integration
    payment_intent_id = Column(Integer, nullable=False, index=True)  # Links to payment domain
    
    # Purchase details
    price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="ETB")
    
    # Status
    status = Column(String(20), nullable=False, default="completed")  # completed, refunded, cancelled
    
    # Metadata
    event_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('payment_intent_id', name='unique_purchase_payment'),
    )


class UserSubscription(MusicBase):
    """
    User subscription model for premium features.
    
    Links to payment domain through payment_intent_id.
    """
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Subscription details
    user_id = Column(String(255), nullable=False, index=True)
    subscription_type = Column(String(50), nullable=False, index=True)  # premium, artist, etc.
    
    # Payment integration
    payment_intent_id = Column(Integer, nullable=True, index=True)  # Links to payment domain
    
    # Subscription period
    status = Column(String(20), nullable=False, default="active")  # active, expired, cancelled
    starts_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Features
    features = Column(JSON, nullable=True, default=list)
    
    # Metadata
    event_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'subscription_type', name='unique_user_subscription'),
    )


class Artist(MusicBase):
    """
    Artist model for music creator management.
    """
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    
    # Artist information
    name = Column(String(255), nullable=False, index=True)
    bio = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # External IDs
    external_id = Column(String(255), nullable=True, index=True)
    
    # Social links
    website_url = Column(String(500), nullable=True)
    social_media = Column(JSON, nullable=True, default=dict)
    
    # Status
    is_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Ownership
    owner_id = Column(String(255), nullable=False, index=True)  # Artist or manager
    
    # Metadata
    artist_metadata = Column(JSON, nullable=True, default=dict)
    tags = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class Release(MusicBase):
    """
    Release model for albums and EPs.
    """
    __tablename__ = "releases"

    id = Column(Integer, primary_key=True, index=True)
    
    # Release information
    title = Column(String(255), nullable=False, index=True)
    release_type = Column(String(50), nullable=False, index=True)  # album, ep, single
    description = Column(Text, nullable=True)
    
    # Artist relationship
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False, index=True)
    
    # Release details
    release_date = Column(DateTime(timezone=True), nullable=True)
    total_tracks = Column(Integer, nullable=False, default=0)
    total_duration_seconds = Column(Integer, nullable=False, default=0)
    
    # Cover art
    cover_image_url = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default="draft")  # draft, published, archived
    is_public = Column(Boolean, nullable=False, default=False)
    
    # External IDs
    external_id = Column(String(255), nullable=True, index=True)
    
    # Metadata
    release_metadata = Column(JSON, nullable=True, default=dict)
    tags = Column(JSON, nullable=True, default=list)
    genres = Column(JSON, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    artist = relationship("Artist", backref="releases")


class ReleaseTrack(MusicBase):
    """
    Junction table for release-track relationships.
    """
    __tablename__ = "release_tracks"

    id = Column(Integer, primary_key=True, index=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("music_songs.id"), nullable=False, index=True)
    
    # Track information
    track_number = Column(Integer, nullable=False)
    disc_number = Column(Integer, nullable=False, default=1)
    
    # Metadata
    track_metadata = Column(JSON, nullable=True, default=dict)

    # Relationships
    release = relationship("Release", backref="tracks")
