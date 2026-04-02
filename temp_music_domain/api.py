"""
Music domain API routers.

This module provides FastAPI routers for music operations
including songs, playlists, marketplace, and social features.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from temp_music_domain.services import (
    SongService, PlaylistService, MarketplaceService, SubscriptionService,
    MusicServiceError, SongNotFoundError, PlaylistNotFoundError, UnauthorizedAccessError
)
from temp_music_domain.schemas import (
    SongCreate, SongUpdate, SongResponse, SongList,
    PlaylistCreate, PlaylistUpdate, PlaylistResponse, PlaylistList, PlaylistSongAdd,
    MarketplaceListingCreate, MarketplaceListingUpdate, MarketplaceListingResponse, MarketplaceList,
    PurchaseCreate, PurchaseResponse,
    SubscriptionCreate, SubscriptionResponse,
    SearchRequest, SearchResponse,
    PlaybackEventCreate, SocialSignalCreate,
    MusicError, APIErrorResponse,
)
from shared.db import get_db
from shared.auth import get_current_user_id, get_optional_user_id
from shared.logging import get_logger
from shared.middleware import get_request_id

logger = get_logger(__name__)

# Create routers
songs_router = APIRouter(prefix="/songs", tags=["songs"])
playlists_router = APIRouter(prefix="/playlists", tags=["playlists"])
marketplace_router = APIRouter(prefix="/marketplace", tags=["marketplace"])
subscriptions_router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
search_router = APIRouter(prefix="/search", tags=["search"])


# Song endpoints
@songs_router.post("/", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
async def create_song(
    request: SongCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Create a new song."""
    try:
        service = SongService(db)
        song = service.create_song(
            title=request.title,
            artist=request.artist,
            file_path=request.file_path,
            uploader_id=user_id,
            owner_id=user_id,
            **request.dict(exclude_unset=True)
        )
        
        logger.info(
            "song_created",
            song_id=song.id,
            user_id=user_id,
            request_id=request_id
        )
        
        return SongResponse.model_validate(song)
        
    except MusicServiceError as e:
        logger.error(
            "song_creation_failed",
            error=str(e),
            user_id=user_id,
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "song_creation_error",
                "message": str(e),
                "request_id": request_id
            }
        )


@songs_router.get("/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: int,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
    request_id: str = Depends(get_request_id),
):
    """Get song by ID."""
    try:
        service = SongService(db)
        song = service.get_song(song_id)
        
        # Check access permissions
        if not song.is_public and song.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "access_denied",
                    "message": "Song is not public",
                    "request_id": request_id
                }
            )
        
        return SongResponse.model_validate(song)
        
    except SongNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "song_not_found",
                "message": str(e),
                "song_id": song_id,
                "request_id": request_id
            }
        )


@songs_router.get("/", response_model=SongList)
async def list_songs(
    user_id: Optional[str] = Depends(get_optional_user_id),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """List songs (public or user's own)."""
    try:
        service = SongService(db)
        
        if user_id:
            # Get user's own songs
            songs = service.get_songs_by_user(user_id, limit, offset)
        else:
            # Get public songs
            songs = service.search_songs("", limit, offset)
        
        return SongList(
            items=[SongResponse.model_validate(song) for song in songs],
            total=len(songs),
            page=offset // limit + 1,
            page_size=limit,
            has_next=len(songs) == limit
        )
        
    except Exception as e:
        logger.error(
            "song_list_failed",
            error=str(e),
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Failed to list songs",
                "request_id": request_id
            }
        )


@songs_router.put("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: int,
    request: SongUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Update song metadata."""
    try:
        service = SongService(db)
        song = service.update_song(
            song_id=song_id,
            user_id=user_id,
            **request.dict(exclude_unset=True)
        )
        
        return SongResponse.model_validate(song)
        
    except SongNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "song_not_found",
                "message": str(e),
                "song_id": song_id,
                "request_id": request_id
            }
        )
    except UnauthorizedAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": str(e),
                "request_id": request_id
            }
        )


@songs_router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_song(
    song_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Delete a song."""
    try:
        service = SongService(db)
        service.delete_song(song_id, user_id)
        
    except SongNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "song_not_found",
                "message": str(e),
                "song_id": song_id,
                "request_id": request_id
            }
        )
    except UnauthorizedAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": str(e),
                "request_id": request_id
            }
        )


@songs_router.post("/{song_id}/playback", status_code=status.HTTP_201_CREATED)
async def record_playback(
    song_id: int,
    request: PlaybackEventCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Record a playback event."""
    try:
        service = SongService(db)
        playback = service.record_playback(
            song_id=song_id,
            user_id=user_id,
            **request.dict(exclude_unset=True)
        )
        
        return {"status": "recorded", "playback_id": playback.id}
        
    except Exception as e:
        logger.error(
            "playback_recording_failed",
            error=str(e),
            song_id=song_id,
            user_id=user_id,
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "playback_error",
                "message": "Failed to record playback",
                "request_id": request_id
            }
        )


@songs_router.post("/{song_id}/signals/{signal_type}", status_code=status.HTTP_201_CREATED)
async def add_social_signal(
    song_id: int,
    signal_type: str,
    request: SocialSignalCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Add social signal to song."""
    try:
        service = SongService(db)
        signal = service.add_social_signal(
            song_id=song_id,
            user_id=user_id,
            signal_type=signal_type,
            **request.dict(exclude_unset=True)
        )
        
        return {"status": "added", "signal_id": signal.id}
        
    except Exception as e:
        logger.error(
            "social_signal_failed",
            error=str(e),
            song_id=song_id,
            user_id=user_id,
            signal_type=signal_type,
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "social_signal_error",
                "message": "Failed to add social signal",
                "request_id": request_id
            }
        )


# Playlist endpoints
@playlists_router.post("/", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    request: PlaylistCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Create a new playlist."""
    try:
        service = PlaylistService(db)
        playlist = service.create_playlist(
            name=request.name,
            owner_id=user_id,
            **request.dict(exclude_unset=True)
        )
        
        return PlaylistResponse.model_validate(playlist)
        
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "playlist_creation_error",
                "message": str(e),
                "request_id": request_id
            }
        )


@playlists_router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
    request_id: str = Depends(get_request_id),
):
    """Get playlist by ID."""
    try:
        service = PlaylistService(db)
        playlist = service.get_playlist(playlist_id)
        
        # Check access permissions
        if not playlist.is_public and playlist.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "access_denied",
                    "message": "Playlist is not public",
                    "request_id": request_id
                }
            )
        
        return PlaylistResponse.model_validate(playlist)
        
    except PlaylistNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "playlist_not_found",
                "message": str(e),
                "playlist_id": playlist_id,
                "request_id": request_id
            }
        )


@playlists_router.get("/", response_model=PlaylistList)
async def list_playlists(
    user_id: Optional[str] = Depends(get_optional_user_id),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """List playlists (public or user's own)."""
    try:
        service = PlaylistService(db)
        
        if user_id:
            # Get user's own playlists
            playlists = service.get_playlists_by_user(user_id, limit, offset)
        else:
            # Get public playlists
            playlists = service.get_public_playlists(limit, offset)
        
        return PlaylistList(
            items=[PlaylistResponse.model_validate(playlist) for playlist in playlists],
            total=len(playlists),
            page=offset // limit + 1,
            page_size=limit,
            has_next=len(playlists) == limit
        )
        
    except Exception as e:
        logger.error(
            "playlist_list_failed",
            error=str(e),
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Failed to list playlists",
                "request_id": request_id
            }
        )


@playlists_router.post("/{playlist_id}/songs", status_code=status.HTTP_201_CREATED)
async def add_song_to_playlist(
    playlist_id: int,
    request: PlaylistSongAdd,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Add song to playlist."""
    try:
        service = PlaylistService(db)
        playlist_song = service.add_song_to_playlist(
            playlist_id=playlist_id,
            song_id=request.song_id,
            user_id=user_id,
            position=request.position,
            **request.dict(exclude_unset=True)
        )
        
        return {"status": "added", "playlist_song_id": playlist_song.id}
        
    except PlaylistNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "playlist_not_found",
                "message": str(e),
                "playlist_id": playlist_id,
                "request_id": request_id
            }
        )
    except UnauthorizedAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": str(e),
                "request_id": request_id
            }
        )
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "playlist_add_error",
                "message": str(e),
                "request_id": request_id
            }
        )


@playlists_router.delete("/{playlist_id}/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Remove song from playlist."""
    try:
        service = PlaylistService(db)
        service.remove_song_from_playlist(playlist_id, song_id, user_id)
        
    except PlaylistNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "playlist_not_found",
                "message": str(e),
                "playlist_id": playlist_id,
                "request_id": request_id
            }
        )
    except UnauthorizedAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "access_denied",
                "message": str(e),
                "request_id": request_id
            }
        )
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "playlist_remove_error",
                "message": str(e),
                "request_id": request_id
            }
        )


# Marketplace endpoints
@marketplace_router.post("/listings", response_model=MarketplaceListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(
    request: MarketplaceListingCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """Create a marketplace listing."""
    try:
        service = MarketplaceService(db)
        listing = service.create_listing(
            item_type=request.item_type,
            item_id=request.item_id,
            price=request.price,
            seller_id=user_id,
            **request.dict(exclude_unset=True)
        )
        
        return MarketplaceListingResponse.model_validate(listing)
        
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "listing_creation_error",
                "message": str(e),
                "request_id": request_id
            }
        )


@marketplace_router.get("/listings", response_model=MarketplaceList)
async def list_marketplace_listings(
    item_type: Optional[str] = Query(None),
    seller_id: Optional[str] = Query(None),
    status: str = Query(default="active"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """List marketplace listings."""
    try:
        service = MarketplaceService(db)
        listings = service.get_listings(
            item_type=item_type,
            seller_id=seller_id,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return MarketplaceList(
            items=[MarketplaceListingResponse.model_validate(listing) for listing in listings],
            total=len(listings),
            page=offset // limit + 1,
            page_size=limit,
            has_next=len(listings) == limit
        )
        
    except Exception as e:
        logger.error(
            "marketplace_list_failed",
            error=str(e),
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Failed to list marketplace items",
                "request_id": request_id
            }
        )


# Search endpoints
@search_router.get("/", response_model=SearchResponse)
async def search(
    query: str = Query(..., min_length=1, max_length=100),
    type: Optional[str] = Query(None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    """Search music content."""
    try:
        song_service = SongService(db)
        playlist_service = PlaylistService(db)
        
        # Search songs
        songs = song_service.search_songs(query, limit, offset) if not type or type == "song" else []
        
        # Search playlists (would need implementation)
        playlists = []  # playlist_service.search_playlists(query, limit, offset) if not type or type == "playlist" else []
        
        return SearchResponse(
            songs=[SongResponse.model_validate(song) for song in songs],
            playlists=[PlaylistResponse.model_validate(playlist) for playlist in playlists],
            artists=[],  # Would need artist service
            releases=[],  # Would need release service
            total=len(songs) + len(playlists),
            query=query,
            type=type
        )
        
    except Exception as e:
        logger.error(
            "search_failed",
            error=str(e),
            query=query,
            request_id=request_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "search_error",
                "message": "Search failed",
                "request_id": request_id
            }
        )


# Export all routers
music_api = APIRouter(prefix="/api/v1/music", tags=["music"])
music_api.include_router(songs_router)
music_api.include_router(playlists_router)
music_api.include_router(marketplace_router)
music_api.include_router(subscriptions_router)
music_api.include_router(search_router)
