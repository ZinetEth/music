from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    device_class = Column(String(20), nullable=False, default="standard")
    is_telegram_user = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    listings = relationship("PlaylistMarketplace", back_populates="seller")
    purchases = relationship("PlaylistPurchase", back_populates="buyer")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="expired")
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="subscriptions")


class PremiumContent(Base):
    __tablename__ = "premium_content"

    id = Column(Integer, primary_key=True, index=True)
    navidrome_song_id = Column(String, nullable=False, unique=True, index=True)
    requires_subscription = Column(Boolean, nullable=False, default=True)


class PlaylistMarketplace(Base):
    __tablename__ = "playlist_marketplace"

    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(String, nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="ETB")
    sales_count = Column(Integer, nullable=False, default=0)
    is_public = Column(Boolean, nullable=False, default=True)

    seller = relationship("User", back_populates="listings")
    purchases = relationship("PlaylistPurchase", back_populates="listing")


class PlaylistPurchase(Base):
    __tablename__ = "playlist_purchases"

    id = Column(Integer, primary_key=True, index=True)
    playlist_listing_id = Column(
        Integer, ForeignKey("playlist_marketplace.id"), nullable=False, index=True
    )
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    listing = relationship("PlaylistMarketplace", back_populates="purchases")
    buyer = relationship("User", back_populates="purchases")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    method = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    user = relationship("User", back_populates="payments")


class HolidayRule(Base):
    __tablename__ = "holiday_rules"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    eth_month = Column(Integer, nullable=False)
    eth_day = Column(Integer, nullable=False)
    recommendations = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


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


class UserPlaybackLog(Base):
    __tablename__ = "user_playback_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    music_id = Column(
        Integer, ForeignKey("music_metadata.id"), nullable=False, index=True
    )
    played_seconds = Column(Float, nullable=False, default=0.0)
    skipped = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)
