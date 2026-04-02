"""
Music domain services.

This module provides business logic for music operations
including playlists, songs, marketplace, and social features.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from temp_music_domain.models import (
    Song, Playlist, PlaylistSong, PlaybackEvent,
    SongSocialSignal, PlaylistSocialSignal, MarketplaceListing,
    Purchase, UserSubscription, Artist, Release, ReleaseTrack
)
from shared.db import utc_now
from shared.logging import get_logger

logger = get_logger(__name__)


class MusicServiceError(Exception):
    """Base exception for music service errors."""
    pass


class SongNotFoundError(MusicServiceError):
    """Raised when song is not found."""
    pass


class PlaylistNotFoundError(MusicServiceError):
    """Raised when playlist is not found."""
    pass


class UnauthorizedAccessError(MusicServiceError):
    """Raised when user doesn't have access to resource."""
    pass


class SongService:
    """Service for song operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_song(
        self,
        title: str,
        artist: str,
        file_path: str,
        uploader_id: str,
        owner_id: str,
        **kwargs
    ) -> Song:
        """Create a new song."""
        song = Song(
            title=title,
            artist=artist,
            file_path=file_path,
            uploader_id=uploader_id,
            owner_id=owner_id,
            **kwargs
        )
        
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        
        logger.info(
            "song_created",
            song_id=song.id,
            title=title,
            artist=artist,
            uploader_id=uploader_id,
            owner_id=owner_id
        )
        
        return song
    
    def get_song(self, song_id: int) -> Song:
        """Get song by ID."""
        song = self.db.query(Song).filter(Song.id == song_id).first()
        if not song:
            raise SongNotFoundError(f"Song {song_id} not found")
        return song
    
    def get_songs_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Song]:
        """Get songs uploaded by user."""
        return (
            self.db.query(Song)
            .filter(Song.uploader_id == user_id)
            .filter(Song.is_active == True)
            .order_by(desc(Song.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def search_songs(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Song]:
        """Search songs by title, artist, or album."""
        search_filter = or_(
            Song.title.ilike(f"%{query}%"),
            Song.artist.ilike(f"%{query}%"),
            Song.album.ilike(f"%{query}%")
        )
        
        return (
            self.db.query(Song)
            .filter(search_filter)
            .filter(Song.is_public == True)
            .filter(Song.is_active == True)
            .order_by(desc(Song.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def update_song(
        self,
        song_id: int,
        user_id: str,
        **kwargs
    ) -> Song:
        """Update song metadata."""
        song = self.get_song(song_id)
        
        # Check ownership
        if song.owner_id != user_id:
            raise UnauthorizedAccessError("User doesn't own this song")
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(song, key):
                setattr(song, key, value)
        
        song.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(song)
        
        logger.info(
            "song_updated",
            song_id=song_id,
            user_id=user_id,
            updated_fields=list(kwargs.keys())
        )
        
        return song
    
    def delete_song(self, song_id: int, user_id: str) -> bool:
        """Soft delete a song."""
        song = self.get_song(song_id)
        
        # Check ownership
        if song.owner_id != user_id:
            raise UnauthorizedAccessError("User doesn't own this song")
        
        song.is_active = False
        song.updated_at = utc_now()
        
        self.db.commit()
        
        logger.info(
            "song_deleted",
            song_id=song_id,
            user_id=user_id
        )
        
        return True
    
    def record_playback(
        self,
        song_id: int,
        user_id: str,
        duration_played: Optional[int] = None,
        completed: bool = False,
        **kwargs
    ) -> PlaybackEvent:
        """Record a playback event."""
        playback = PlaybackEvent(
            song_id=song_id,
            user_id=user_id,
            duration_played_seconds=duration_played,
            completed=completed,
            **kwargs
        )
        
        self.db.add(playback)
        self.db.commit()
        self.db.refresh(playback)
        
        # Update song's last played time
        song = self.get_song(song_id)
        song.last_played_at = playback.played_at
        self.db.commit()
        
        return playback
    
    def add_social_signal(
        self,
        song_id: int,
        user_id: str,
        signal_type: str,
        signal_value: float = 1.0,
        **kwargs
    ) -> SongSocialSignal:
        """Add social signal to song."""
        # Check if signal already exists
        existing = (
            self.db.query(SongSocialSignal)
            .filter(
                and_(
                    SongSocialSignal.song_id == song_id,
                    SongSocialSignal.user_id == user_id,
                    SongSocialSignal.signal_type == signal_type
                )
            )
            .first()
        )
        
        if existing:
            # Update existing signal
            existing.signal_value = signal_value
            existing.metadata = kwargs
            signal = existing
        else:
            # Create new signal
            signal = SongSocialSignal(
                song_id=song_id,
                user_id=user_id,
                signal_type=signal_type,
                signal_value=signal_value,
                metadata=kwargs
            )
            self.db.add(signal)
        
        self.db.commit()
        self.db.refresh(signal)
        
        return signal


class PlaylistService:
    """Service for playlist operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_playlist(
        self,
        name: str,
        owner_id: str,
        **kwargs
    ) -> Playlist:
        """Create a new playlist."""
        playlist = Playlist(
            name=name,
            owner_id=owner_id,
            **kwargs
        )
        
        self.db.add(playlist)
        self.db.commit()
        self.db.refresh(playlist)
        
        logger.info(
            "playlist_created",
            playlist_id=playlist.id,
            name=name,
            owner_id=owner_id
        )
        
        return playlist
    
    def get_playlist(self, playlist_id: int) -> Playlist:
        """Get playlist by ID."""
        playlist = self.db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise PlaylistNotFoundError(f"Playlist {playlist_id} not found")
        return playlist
    
    def get_playlists_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Playlist]:
        """Get playlists owned by user."""
        return (
            self.db.query(Playlist)
            .filter(Playlist.owner_id == user_id)
            .filter(Playlist.is_active == True)
            .order_by(desc(Playlist.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_public_playlists(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Playlist]:
        """Get public playlists."""
        return (
            self.db.query(Playlist)
            .filter(Playlist.is_public == True)
            .filter(Playlist.is_active == True)
            .order_by(desc(Playlist.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def add_song_to_playlist(
        self,
        playlist_id: int,
        song_id: int,
        user_id: str,
        position: Optional[int] = None
    ) -> PlaylistSong:
        """Add song to playlist."""
        playlist = self.get_playlist(playlist_id)
        
        # Check ownership
        if playlist.owner_id != user_id:
            raise UnauthorizedAccessError("User doesn't own this playlist")
        
        # Check if song already exists in playlist
        existing = (
            self.db.query(PlaylistSong)
            .filter(
                and_(
                    PlaylistSong.playlist_id == playlist_id,
                    PlaylistSong.song_id == song_id
                )
            )
            .first()
        )
        
        if existing:
            raise MusicServiceError("Song already in playlist")
        
        # Get next position if not provided
        if position is None:
            max_position = (
                self.db.query(func.max(PlaylistSong.position))
                .filter(PlaylistSong.playlist_id == playlist_id)
                .scalar() or 0
            )
            position = max_position + 1
        
        playlist_song = PlaylistSong(
            playlist_id=playlist_id,
            song_id=song_id,
            position=position,
            added_by=user_id
        )
        
        self.db.add(playlist_song)
        
        # Update playlist metadata
        playlist.song_count += 1
        playlist.updated_at = utc_now()
        
        self.db.commit()
        self.db.refresh(playlist_song)
        
        logger.info(
            "song_added_to_playlist",
            playlist_id=playlist_id,
            song_id=song_id,
            user_id=user_id,
            position=position
        )
        
        return playlist_song
    
    def remove_song_from_playlist(
        self,
        playlist_id: int,
        song_id: int,
        user_id: str
    ) -> bool:
        """Remove song from playlist."""
        playlist = self.get_playlist(playlist_id)
        
        # Check ownership
        if playlist.owner_id != user_id:
            raise UnauthorizedAccessError("User doesn't own this playlist")
        
        playlist_song = (
            self.db.query(PlaylistSong)
            .filter(
                and_(
                    PlaylistSong.playlist_id == playlist_id,
                    PlaylistSong.song_id == song_id
                )
            )
            .first()
        )
        
        if not playlist_song:
            raise MusicServiceError("Song not in playlist")
        
        self.db.delete(playlist_song)
        
        # Update playlist metadata
        playlist.song_count = max(0, playlist.song_count - 1)
        playlist.updated_at = utc_now()
        
        self.db.commit()
        
        logger.info(
            "song_removed_from_playlist",
            playlist_id=playlist_id,
            song_id=song_id,
            user_id=user_id
        )
        
        return True
    
    def update_playlist(
        self,
        playlist_id: int,
        user_id: str,
        **kwargs
    ) -> Playlist:
        """Update playlist metadata."""
        playlist = self.get_playlist(playlist_id)
        
        # Check ownership
        if playlist.owner_id != user_id:
            raise UnauthorizedAccessError("User doesn't own this playlist")
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(playlist, key):
                setattr(playlist, key, value)
        
        playlist.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(playlist)
        
        return playlist
    
    def delete_playlist(self, playlist_id: int, user_id: str) -> bool:
        """Soft delete a playlist."""
        playlist = self.get_playlist(playlist_id)
        
        # Check ownership
        if playlist.owner_id != user_id:
            raise UnauthorizedAccessError("User doesn't own this playlist")
        
        playlist.is_active = False
        playlist.updated_at = utc_now()
        
        self.db.commit()
        
        logger.info(
            "playlist_deleted",
            playlist_id=playlist_id,
            user_id=user_id
        )
        
        return True


class MarketplaceService:
    """Service for marketplace operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_listing(
        self,
        item_type: str,
        item_id: int,
        price: float,
        seller_id: str,
        **kwargs
    ) -> MarketplaceListing:
        """Create a marketplace listing."""
        listing = MarketplaceListing(
            item_type=item_type,
            item_id=item_id,
            price=price,
            seller_id=seller_id,
            **kwargs
        )
        
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        
        logger.info(
            "marketplace_listing_created",
            listing_id=listing.id,
            item_type=item_type,
            item_id=item_id,
            price=price,
            seller_id=seller_id
        )
        
        return listing
    
    def get_listings(
        self,
        item_type: Optional[str] = None,
        seller_id: Optional[str] = None,
        status: str = "active",
        limit: int = 50,
        offset: int = 0
    ) -> List[MarketplaceListing]:
        """Get marketplace listings with filters."""
        query = self.db.query(MarketplaceListing)
        
        if item_type:
            query = query.filter(MarketplaceListing.item_type == item_type)
        
        if seller_id:
            query = query.filter(MarketplaceListing.seller_id == seller_id)
        
        if status:
            query = query.filter(MarketplaceListing.status == status)
        
        return (
            query.order_by(desc(MarketplaceListing.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def create_purchase(
        self,
        buyer_id: str,
        seller_id: str,
        item_type: str,
        item_id: int,
        price: float,
        payment_intent_id: int,
        **kwargs
    ) -> Purchase:
        """Create a purchase record."""
        purchase = Purchase(
            buyer_id=buyer_id,
            seller_id=seller_id,
            item_type=item_type,
            item_id=item_id,
            price=price,
            payment_intent_id=payment_intent_id,
            **kwargs
        )
        
        self.db.add(purchase)
        self.db.commit()
        self.db.refresh(purchase)
        
        # Update listing sales count
        listing = (
            self.db.query(MarketplaceListing)
            .filter(
                and_(
                    MarketplaceListing.item_type == item_type,
                    MarketplaceListing.item_id == item_id,
                    MarketplaceListing.seller_id == seller_id
                )
            )
            .first()
        )
        
        if listing:
            listing.sales_count += 1
            listing.total_revenue += price
            self.db.commit()
        
        logger.info(
            "purchase_created",
            purchase_id=purchase.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            item_type=item_type,
            item_id=item_id,
            price=price,
            payment_intent_id=payment_intent_id
        )
        
        return purchase


class SubscriptionService:
    """Service for subscription operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_subscription(
        self,
        user_id: str,
        subscription_type: str,
        payment_intent_id: Optional[int] = None,
        **kwargs
    ) -> UserSubscription:
        """Create a user subscription."""
        # Check if subscription already exists
        existing = (
            self.db.query(UserSubscription)
            .filter(
                and_(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_type == subscription_type,
                    UserSubscription.status == "active"
                )
            )
            .first()
        )
        
        if existing:
            raise MusicServiceError("User already has active subscription")
        
        subscription = UserSubscription(
            user_id=user_id,
            subscription_type=subscription_type,
            payment_intent_id=payment_intent_id,
            **kwargs
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(
            "subscription_created",
            subscription_id=subscription.id,
            user_id=user_id,
            subscription_type=subscription_type,
            payment_intent_id=payment_intent_id
        )
        
        return subscription
    
    def get_user_subscription(
        self,
        user_id: str,
        subscription_type: Optional[str] = None
    ) -> Optional[UserSubscription]:
        """Get user's active subscription."""
        query = self.db.query(UserSubscription).filter(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status == "active"
            )
        )
        
        if subscription_type:
            query = query.filter(UserSubscription.subscription_type == subscription_type)
        
        return query.order_by(desc(UserSubscription.created_at)).first()
    
    def cancel_subscription(
        self,
        user_id: str,
        subscription_type: str
    ) -> bool:
        """Cancel user's subscription."""
        subscription = self.get_user_subscription(user_id, subscription_type)
        
        if not subscription:
            raise MusicServiceError("No active subscription found")
        
        subscription.status = "cancelled"
        subscription.cancelled_at = utc_now()
        subscription.updated_at = utc_now()
        
        self.db.commit()
        
        logger.info(
            "subscription_cancelled",
            subscription_id=subscription.id,
            user_id=user_id,
            subscription_type=subscription_type
        )
        
        return True
