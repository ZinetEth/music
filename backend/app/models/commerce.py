from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.utils.helpers import utc_now


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
    playlist_listing_id = Column(Integer, ForeignKey("playlist_marketplace.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    listing = relationship("PlaylistMarketplace", back_populates="purchases")
    buyer = relationship("User", back_populates="purchases")


class SongMarketplace(Base):
    __tablename__ = "song_marketplace"

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(String(255), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="ETB")
    sales_count = Column(Integer, nullable=False, default=0)
    is_public = Column(Boolean, nullable=False, default=True)

    seller = relationship("User", back_populates="song_listings")
    purchases = relationship("SongPurchase", back_populates="listing")


class SongPurchase(Base):
    __tablename__ = "song_purchases"

    id = Column(Integer, primary_key=True, index=True)
    song_listing_id = Column(Integer, ForeignKey("song_marketplace.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    listing = relationship("SongMarketplace", back_populates="purchases")
    buyer = relationship("User", back_populates="song_purchases")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    method = Column(String(20), nullable=False)
    payment_type = Column(String(50), nullable=True)
    playlist_id = Column(String(255), nullable=True, index=True)
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
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

