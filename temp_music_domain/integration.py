"""
Music-Payment Domain Integration Layer.

This module provides integration between the music domain and payment domain,
ensuring clean separation while enabling complete functionality.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from temp_music_domain.services import (
    SongService, PlaylistService, MarketplaceService, SubscriptionService,
    MusicServiceError
)
from temp_music_domain.schemas import (
    SongResponse, PlaylistResponse, MarketplaceListingResponse,
    PurchaseResponse, SubscriptionResponse
)
from shared.db import get_db
from shared.logging import get_logger

logger = get_logger(__name__)


class MusicPaymentIntegration:
    """
    Integration layer between music and payment domains.
    
    This class handles the business logic that connects
    music operations with payment processing.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.song_service = SongService(db)
        self.playlist_service = PlaylistService(db)
        self.marketplace_service = MarketplaceService(db)
        self.subscription_service = SubscriptionService(db)
    
    async def purchase_song(
        self,
        song_id: int,
        buyer_id: str,
        payment_provider: str = "telebirr"
    ) -> Dict[str, Any]:
        """
        Purchase a song using payment domain.
        
        Args:
            song_id: ID of song to purchase
            buyer_id: ID of buyer
            payment_provider: Payment provider to use
            
        Returns:
            Purchase result with payment intent
        """
        try:
            # Get song details
            song = self.song_service.get_song(song_id)
            
            # Create marketplace listing if not exists
            listing = self._ensure_song_listing(song_id, song.owner_id)
            
            # Create payment intent through payment domain
            from apps.payments.services.payment_service import PaymentService
            from apps.payments.schemas import PaymentIntentCreate
            
            payment_service = PaymentService(self.db)
            payment_intent = await payment_service.create_payment_intent(
                PaymentIntentCreate(
                    app_name="music_platform",
                    object_type="song",
                    object_id=str(song_id),
                    amount=listing.price,
                    currency=listing.currency,
                    customer_id=buyer_id,
                    merchant_id=song.owner_id,
                    description=f"Purchase song: {song.title}",
                    success_url=f"/api/v1/music/songs/{song_id}",
                    cancel_url=f"/api/v1/music/songs/{song_id}",
                    webhook_url="/api/v1/payments/webhooks/telebirr"
                )
            )
            
            logger.info(
                "song_purchase_initiated",
                song_id=song_id,
                buyer_id=buyer_id,
                seller_id=song.owner_id,
                price=listing.price,
                payment_intent_id=payment_intent.id
            )
            
            return {
                "status": "payment_required",
                "song": SongResponse.model_validate(song),
                "listing": listing,
                "payment_intent": payment_intent,
                "next_action": "process_payment"
            }
            
        except MusicServiceError as e:
            logger.error(
                "song_purchase_failed",
                error=str(e),
                song_id=song_id,
                buyer_id=buyer_id
            )
            raise
    
    async def purchase_playlist(
        self,
        playlist_id: int,
        buyer_id: str,
        payment_provider: str = "telebirr"
    ) -> Dict[str, Any]:
        """
        Purchase a playlist using payment domain.
        
        Args:
            playlist_id: ID of playlist to purchase
            buyer_id: ID of buyer
            payment_provider: Payment provider to use
            
        Returns:
            Purchase result with payment intent
        """
        try:
            # Get playlist details
            playlist = self.playlist_service.get_playlist(playlist_id)
            
            # Create marketplace listing if not exists
            listing = self._ensure_playlist_listing(playlist_id, playlist.owner_id)
            
            # Create payment intent through payment domain
            from apps.payments.services.payment_service import PaymentService
            from apps.payments.schemas import PaymentIntentCreate
            
            payment_service = PaymentService(self.db)
            payment_intent = await payment_service.create_payment_intent(
                PaymentIntentCreate(
                    app_name="music_platform",
                    object_type="playlist",
                    object_id=str(playlist_id),
                    amount=listing.price,
                    currency=listing.currency,
                    customer_id=buyer_id,
                    merchant_id=playlist.owner_id,
                    description=f"Purchase playlist: {playlist.name}",
                    success_url=f"/api/v1/music/playlists/{playlist_id}",
                    cancel_url=f"/api/v1/music/playlists/{playlist_id}",
                    webhook_url="/api/v1/payments/webhooks/telebirr"
                )
            )
            
            logger.info(
                "playlist_purchase_initiated",
                playlist_id=playlist_id,
                buyer_id=buyer_id,
                seller_id=playlist.owner_id,
                price=listing.price,
                payment_intent_id=payment_intent.id
            )
            
            return {
                "status": "payment_required",
                "playlist": PlaylistResponse.model_validate(playlist),
                "listing": listing,
                "payment_intent": payment_intent,
                "next_action": "process_payment"
            }
            
        except MusicServiceError as e:
            logger.error(
                "playlist_purchase_failed",
                error=str(e),
                playlist_id=playlist_id,
                buyer_id=buyer_id
            )
            raise
    
    async def purchase_subscription(
        self,
        subscription_type: str,
        user_id: str,
        payment_provider: str = "telebirr"
    ) -> Dict[str, Any]:
        """
        Purchase a subscription using payment domain.
        
        Args:
            subscription_type: Type of subscription
            user_id: ID of user
            payment_provider: Payment provider to use
            
        Returns:
            Purchase result with payment intent
        """
        try:
            # Get subscription pricing
            from temp_music_domain.config import get_music_config
            config = get_music_config()
            
            if subscription_type == "premium":
                price = config.premium_price_monthly
                description = "Premium monthly subscription"
            elif subscription_type == "premium_yearly":
                price = config.premium_price_yearly
                description = "Premium yearly subscription"
            else:
                raise MusicServiceError(f"Unknown subscription type: {subscription_type}")
            
            # Create payment intent through payment domain
            from apps.payments.services.payment_service import PaymentService
            from apps.payments.schemas import PaymentIntentCreate
            
            payment_service = PaymentService(self.db)
            payment_intent = await payment_service.create_payment_intent(
                PaymentIntentCreate(
                    app_name="music_platform",
                    object_type="subscription",
                    object_id=subscription_type,
                    amount=price,
                    currency="ETB",
                    customer_id=user_id,
                    description=description,
                    success_url="/api/v1/music/subscriptions",
                    cancel_url="/api/v1/music/subscriptions",
                    webhook_url="/api/v1/payments/webhooks/telebirr"
                )
            )
            
            logger.info(
                "subscription_purchase_initiated",
                subscription_type=subscription_type,
                user_id=user_id,
                price=price,
                payment_intent_id=payment_intent.id
            )
            
            return {
                "status": "payment_required",
                "subscription_type": subscription_type,
                "price": price,
                "payment_intent": payment_intent,
                "next_action": "process_payment"
            }
            
        except Exception as e:
            logger.error(
                "subscription_purchase_failed",
                error=str(e),
                subscription_type=subscription_type,
                user_id=user_id
            )
            raise
    
    def complete_purchase(
        self,
        payment_intent_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Complete a purchase after payment verification.
        
        Args:
            payment_intent_id: ID of verified payment intent
            user_id: ID of user completing purchase
            
        Returns:
            Purchase completion result
        """
        try:
            # Get payment intent details
            from apps.payments.services.payment_service import PaymentService
            payment_service = PaymentService(self.db)
            payment_intent = payment_service.get_payment_intent(payment_intent_id)
            
            if payment_intent.status != "completed":
                raise MusicServiceError("Payment not completed")
            
            # Create purchase record based on object type
            if payment_intent.object_type == "song":
                song_id = int(payment_intent.object_id)
                song = self.song_service.get_song(song_id)
                
                purchase = self.marketplace_service.create_purchase(
                    buyer_id=user_id,
                    seller_id=song.owner_id,
                    item_type="song",
                    item_id=song_id,
                    price=float(payment_intent.amount),
                    payment_intent_id=payment_intent_id,
                    metadata={"payment_provider": "telebirr"}
                )
                
                result = {
                    "status": "completed",
                    "purchase_type": "song",
                    "song": SongResponse.model_validate(song),
                    "purchase": PurchaseResponse.model_validate(purchase)
                }
                
            elif payment_intent.object_type == "playlist":
                playlist_id = int(payment_intent.object_id)
                playlist = self.playlist_service.get_playlist(playlist_id)
                
                purchase = self.marketplace_service.create_purchase(
                    buyer_id=user_id,
                    seller_id=playlist.owner_id,
                    item_type="playlist",
                    item_id=playlist_id,
                    price=float(payment_intent.amount),
                    payment_intent_id=payment_intent_id,
                    metadata={"payment_provider": "telebirr"}
                )
                
                result = {
                    "status": "completed",
                    "purchase_type": "playlist",
                    "playlist": PlaylistResponse.model_validate(playlist),
                    "purchase": PurchaseResponse.model_validate(purchase)
                }
                
            elif payment_intent.object_type == "subscription":
                subscription = self.subscription_service.create_subscription(
                    user_id=user_id,
                    subscription_type=payment_intent.object_id,
                    payment_intent_id=payment_intent_id
                )
                
                result = {
                    "status": "completed",
                    "purchase_type": "subscription",
                    "subscription": SubscriptionResponse.model_validate(subscription)
                }
                
            else:
                raise MusicServiceError(f"Unknown object type: {payment_intent.object_type}")
            
            logger.info(
                "purchase_completed",
                payment_intent_id=payment_intent_id,
                user_id=user_id,
                purchase_type=result["purchase_type"]
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "purchase_completion_failed",
                error=str(e),
                payment_intent_id=payment_intent_id,
                user_id=user_id
            )
            raise
    
    def _ensure_song_listing(
        self,
        song_id: int,
        owner_id: str,
        price: Optional[float] = None
    ) -> MarketplaceListingResponse:
        """Ensure song has marketplace listing."""
        # Check if listing exists
        existing_listings = self.marketplace_service.get_listings(
            item_type="song",
            item_id=song_id,
            seller_id=owner_id,
            status="active",
            limit=1
        )
        
        if existing_listings:
            return MarketplaceListingResponse.model_validate(existing_listings[0])
        
        # Create default listing
        from temp_music_domain.config import get_music_config
        config = get_music_config()
        
        default_price = price or config.min_listing_price
        listing = self.marketplace_service.create_listing(
            item_type="song",
            item_id=song_id,
            price=default_price,
            seller_id=owner_id,
            title=f"Song: {song_id}",
            description="Purchase this song",
            metadata={"auto_generated": True}
        )
        
        return MarketplaceListingResponse.model_validate(listing)
    
    def _ensure_playlist_listing(
        self,
        playlist_id: int,
        owner_id: str,
        price: Optional[float] = None
    ) -> MarketplaceListingResponse:
        """Ensure playlist has marketplace listing."""
        # Check if listing exists
        existing_listings = self.marketplace_service.get_listings(
            item_type="playlist",
            item_id=playlist_id,
            seller_id=owner_id,
            status="active",
            limit=1
        )
        
        if existing_listings:
            return MarketplaceListingResponse.model_validate(existing_listings[0])
        
        # Create default listing
        from temp_music_domain.config import get_music_config
        config = get_music_config()
        
        default_price = price or config.min_listing_price
        listing = self.marketplace_service.create_listing(
            item_type="playlist",
            item_id=playlist_id,
            price=default_price,
            seller_id=owner_id,
            title=f"Playlist: {playlist_id}",
            description="Purchase this playlist",
            metadata={"auto_generated": True}
        )
        
        return MarketplaceListingResponse.model_validate(listing)
    
    def get_user_purchases(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's purchase history."""
        # This would query purchases and join with items
        # For now, return placeholder
        return []
    
    def get_user_revenue(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get user's revenue from sales."""
        # This would calculate revenue from marketplace sales
        # For now, return placeholder
        return {
            "total_revenue": 0.0,
            "total_sales": 0,
            "period": {
                "start": start_date,
                "end": end_date
            }
        }


# Integration API endpoints
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status

integration_router = APIRouter(prefix="/api/v1/integration", tags=["integration"])


@integration_router.post("/purchase/song/{song_id}")
async def purchase_song_endpoint(
    song_id: int,
    payment_provider: str = Query(default="telebirr"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Purchase a song."""
    integration = MusicPaymentIntegration(db)
    
    try:
        result = await integration.purchase_song(song_id, user_id, payment_provider)
        return result
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "purchase_failed", "message": str(e)}
        )


@integration_router.post("/purchase/playlist/{playlist_id}")
async def purchase_playlist_endpoint(
    playlist_id: int,
    payment_provider: str = Query(default="telebirr"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Purchase a playlist."""
    integration = MusicPaymentIntegration(db)
    
    try:
        result = await integration.purchase_playlist(playlist_id, user_id, payment_provider)
        return result
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "purchase_failed", "message": str(e)}
        )


@integration_router.post("/purchase/subscription/{subscription_type}")
async def purchase_subscription_endpoint(
    subscription_type: str,
    payment_provider: str = Query(default="telebirr"),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Purchase a subscription."""
    integration = MusicPaymentIntegration(db)
    
    try:
        result = await integration.purchase_subscription(subscription_type, user_id, payment_provider)
        return result
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "purchase_failed", "message": str(e)}
        )


@integration_router.post("/complete/{payment_intent_id}")
async def complete_purchase_endpoint(
    payment_intent_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Complete a purchase after payment verification."""
    integration = MusicPaymentIntegration(db)
    
    try:
        result = integration.complete_purchase(payment_intent_id, user_id)
        return result
    except MusicServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "completion_failed", "message": str(e)}
        )


@integration_router.get("/purchases")
async def get_purchases_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get user's purchase history."""
    integration = MusicPaymentIntegration(db)
    
    try:
        purchases = integration.get_user_purchases(user_id, limit, offset)
        return {
            "purchases": purchases,
            "total": len(purchases),
            "page": offset // limit + 1,
            "page_size": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )


@integration_router.get("/revenue")
async def get_revenue_endpoint(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get user's revenue from sales."""
    integration = MusicPaymentIntegration(db)
    
    try:
        revenue = integration.get_user_revenue(user_id, start_date, end_date)
        return revenue
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )
