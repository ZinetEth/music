"""
Music domain schemas.

This module defines Pydantic schemas for music API
including songs, playlists, marketplace, and social features.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# Base schemas
class BaseMusicSchema(BaseModel):
    """Base schema for music operations."""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# Song schemas
class SongCreate(BaseModel):
    """Create a new song."""
    title: str = Field(..., min_length=1, max_length=255)
    artist: str = Field(..., min_length=1, max_length=255)
    album: Optional[str] = Field(None, max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    duration_seconds: Optional[int] = Field(None, ge=0)
    file_path: str = Field(..., min_length=1, max_length=500)
    file_size_bytes: Optional[int] = Field(None, ge=0)
    format: Optional[str] = Field(None, max_length=10)
    bitrate: Optional[int] = Field(None, ge=0)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    track_number: Optional[int] = Field(None, ge=1)
    lyrics: Optional[str] = Field(None, max_length=10000)
    external_id: Optional[str] = Field(None, max_length=255)
    isrc: Optional[str] = Field(None, max_length=12)
    is_explicit: bool = Field(default=False)
    is_public: bool = Field(default=True)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)


class SongUpdate(BaseModel):
    """Update song metadata."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    artist: Optional[str] = Field(None, min_length=1, max_length=255)
    album: Optional[str] = Field(None, max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    duration_seconds: Optional[int] = Field(None, ge=0)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    track_number: Optional[int] = Field(None, ge=1)
    lyrics: Optional[str] = Field(None, max_length=10000)
    is_explicit: Optional[bool] = None
    is_public: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class SongResponse(BaseMusicSchema):
    """Song response."""
    id: int
    title: str
    artist: str
    album: Optional[str]
    genre: Optional[str]
    duration_seconds: Optional[int]
    file_path: str
    file_size_bytes: Optional[int]
    format: Optional[str]
    bitrate: Optional[int]
    year: Optional[int]
    track_number: Optional[int]
    lyrics: Optional[str]
    external_id: Optional[str]
    isrc: Optional[str]
    is_active: bool
    is_explicit: bool
    is_public: bool
    uploader_id: str
    owner_id: str
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    last_played_at: Optional[datetime]


class PlaybackEventCreate(BaseModel):
    """Create a playback event."""
    song_id: int = Field(..., gt=0)
    duration_played_seconds: Optional[int] = Field(None, ge=0)
    completed: bool = Field(default=False)
    source: Optional[str] = Field(None, max_length=50)
    source_id: Optional[str] = Field(None, max_length=255)
    device_type: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SocialSignalCreate(BaseModel):
    """Create a social signal."""
    signal_type: str = Field(..., max_length=50)
    signal_value: float = Field(default=1.0, ge=0.0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Playlist schemas
class PlaylistCreate(BaseModel):
    """Create a new playlist."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_public: bool = Field(default=True)
    is_collaborative: bool = Field(default=False)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    external_id: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)


class PlaylistUpdate(BaseModel):
    """Update playlist metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_public: Optional[bool] = None
    is_collaborative: Optional[bool] = None
    cover_image_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class PlaylistResponse(BaseMusicSchema):
    """Playlist response."""
    id: int
    name: str
    description: Optional[str]
    owner_id: str
    is_public: bool
    is_collaborative: bool
    song_count: int
    total_duration_seconds: int
    cover_image_url: Optional[str]
    is_active: bool
    external_id: Optional[str]
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime]


class PlaylistSongAdd(BaseModel):
    """Add song to playlist."""
    song_id: int = Field(..., gt=0)
    position: Optional[int] = Field(None, ge=1)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PlaylistSongResponse(BaseMusicSchema):
    """Playlist song response."""
    id: int
    playlist_id: int
    song_id: int
    position: int
    added_by: str
    added_at: datetime
    metadata: Dict[str, Any]
    song: Optional[SongResponse]


# Marketplace schemas
class MarketplaceListingCreate(BaseModel):
    """Create a marketplace listing."""
    item_type: str = Field(..., max_length=50)
    item_id: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    currency: str = Field(default="ETB", max_length=3)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None


class MarketplaceListingUpdate(BaseModel):
    """Update marketplace listing."""
    price: Optional[float] = Field(None, gt=0)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_featured: Optional[bool] = None
    expires_at: Optional[datetime] = None


class MarketplaceListingResponse(BaseMusicSchema):
    """Marketplace listing response."""
    id: int
    item_type: str
    item_id: int
    price: float
    currency: str
    seller_id: str
    status: str
    is_featured: bool
    sales_count: int
    total_revenue: float
    title: Optional[str]
    description: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    item: Optional[Dict[str, Any]]  # Populated from service layer


class PurchaseCreate(BaseModel):
    """Create a purchase record."""
    buyer_id: str = Field(..., min_length=1, max_length=255)
    seller_id: str = Field(..., min_length=1, max_length=255)
    item_type: str = Field(..., max_length=50)
    item_id: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    currency: str = Field(default="ETB", max_length=3)
    payment_intent_id: int = Field(..., gt=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PurchaseResponse(BaseMusicSchema):
    """Purchase response."""
    id: int
    buyer_id: str
    seller_id: str
    item_type: str
    item_id: int
    price: float
    currency: str
    payment_intent_id: int
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    refunded_at: Optional[datetime]


# Subscription schemas
class SubscriptionCreate(BaseModel):
    """Create a user subscription."""
    subscription_type: str = Field(..., max_length=50)
    payment_intent_id: Optional[int] = Field(None, gt=0)
    features: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SubscriptionUpdate(BaseModel):
    """Update subscription."""
    features: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class SubscriptionResponse(BaseMusicSchema):
    """Subscription response."""
    id: int
    user_id: str
    subscription_type: str
    payment_intent_id: Optional[int]
    status: str
    starts_at: datetime
    expires_at: Optional[datetime]
    features: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime]


# Artist schemas
class ArtistCreate(BaseModel):
    """Create an artist."""
    name: str = Field(..., min_length=1, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    external_id: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    social_media: Optional[Dict[str, str]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)


class ArtistUpdate(BaseModel):
    """Update artist."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)
    social_media: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class ArtistResponse(BaseMusicSchema):
    """Artist response."""
    id: int
    name: str
    bio: Optional[str]
    image_url: Optional[str]
    external_id: Optional[str]
    website_url: Optional[str]
    social_media: Dict[str, str]
    is_verified: bool
    is_active: bool
    owner_id: str
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime


# Release schemas
class ReleaseCreate(BaseModel):
    """Create a release."""
    title: str = Field(..., min_length=1, max_length=255)
    release_type: str = Field(..., max_length=50)
    artist_id: int = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    release_date: Optional[datetime] = None
    cover_image_url: Optional[str] = Field(None, max_length=500)
    external_id: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)
    genres: Optional[List[str]] = Field(default_factory=list)


class ReleaseUpdate(BaseModel):
    """Update release."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    release_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    release_date: Optional[datetime] = None
    cover_image_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class ReleaseResponse(BaseMusicSchema):
    """Release response."""
    id: int
    title: str
    release_type: str
    artist_id: int
    description: Optional[str]
    release_date: Optional[datetime]
    total_tracks: int
    total_duration_seconds: int
    cover_image_url: Optional[str]
    status: str
    is_public: bool
    external_id: Optional[str]
    metadata: Dict[str, Any]
    tags: List[str]
    genres: List[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    artist: Optional[ArtistResponse]


# List and filter schemas
class SongList(BaseModel):
    """Song list response."""
    items: List[SongResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class PlaylistList(BaseModel):
    """Playlist list response."""
    items: List[PlaylistResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class MarketplaceList(BaseModel):
    """Marketplace list response."""
    items: List[MarketplaceListingResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class ArtistList(BaseModel):
    """Artist list response."""
    items: List[ArtistResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class ReleaseList(BaseModel):
    """Release list response."""
    items: List[ReleaseResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# Search schemas
class SearchRequest(BaseModel):
    """Search request."""
    query: str = Field(..., min_length=1, max_length=100)
    type: Optional[str] = Field(None, max_length=50)  # song, playlist, artist, album
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchResponse(BaseModel):
    """Search response."""
    songs: List[SongResponse]
    playlists: List[PlaylistResponse]
    artists: List[ArtistResponse]
    releases: List[ReleaseResponse]
    total: int
    query: str
    type: Optional[str]


# Error response schemas
class MusicError(BaseModel):
    """Music domain error response."""
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class ValidationError(BaseModel):
    """Validation error response."""
    field: str
    message: str
    code: str


class APIErrorResponse(BaseModel):
    """General API error response."""
    error: str
    message: str
    error_code: str
    validation_errors: Optional[List[ValidationError]] = None
    timestamp: datetime
    request_id: Optional[str] = None


# Statistics schemas
class SongStats(BaseModel):
    """Song statistics."""
    total_songs: int
    public_songs: int
    total_plays: int
    unique_artists: int
    top_genres: List[Dict[str, Any]]
    period_start: datetime
    period_end: datetime


class PlaylistStats(BaseModel):
    """Playlist statistics."""
    total_playlists: int
    public_playlists: int
    total_songs_in_playlists: int
    average_songs_per_playlist: float
    period_start: datetime
    period_end: datetime


class MarketplaceStats(BaseModel):
    """Marketplace statistics."""
    total_listings: int
    active_listings: int
    total_sales: int
    total_revenue: float
    average_price: float
    period_start: datetime
    period_end: datetime
