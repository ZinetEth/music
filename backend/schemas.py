from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DeviceClass = Literal["lite", "standard", "high"]
SubscriptionStatus = Literal["active", "expired"]
PaymentMethod = Literal["telebirr", "cbe"]
PaymentStatus = Literal["pending", "confirmed"]


class DeviceRegister(BaseModel):
    user_agent: str = Field(..., min_length=1)
    telegram: bool = False
    telegram_id: str | None = None
    email: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: str | None
    email: str | None
    device_class: DeviceClass
    is_telegram_user: bool
    created_at: datetime


class RegisterDeviceResponse(BaseModel):
    user_id: int
    device_class: DeviceClass


class CanPlayResponse(BaseModel):
    allowed: bool


class StreamPolicyResponse(BaseModel):
    device_class: DeviceClass
    maxBitrate: int


class PremiumSongOut(BaseModel):
    navidrome_song_id: str


class SellPlaylistRequest(BaseModel):
    playlist_id: str
    seller_id: int
    price: float = Field(..., gt=0)
    currency: str = "ETB"
    is_public: bool = True


class MarketplaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    playlist_id: str
    seller_id: int
    price: float
    currency: str
    sales_count: int
    is_public: bool


class BuyPlaylistRequest(BaseModel):
    playlist_id: str
    buyer_id: int


class BuyPlaylistResponse(BaseModel):
    playlist_id: str
    buyer_id: int
    sales_count: int
    purchased: bool


class PaymentCreateRequest(BaseModel):
    user_id: int
    amount: float = Field(..., gt=0)
    method: PaymentMethod


class PaymentConfirmRequest(BaseModel):
    payment_id: int


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount: float
    method: PaymentMethod
    status: PaymentStatus
    created_at: datetime


class PaymentConfirmResponse(BaseModel):
    payment_id: int
    status: PaymentStatus
    subscription_status: SubscriptionStatus
    expires_at: datetime


class GregorianDateIn(BaseModel):
    year: int
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)


class EthiopianDateIn(BaseModel):
    year: int
    month: int = Field(..., ge=1, le=13)
    day: int = Field(..., ge=1, le=30)


class EthiopianDateOut(BaseModel):
    year: int
    month: int
    day: int


class PlaylistRecommendation(BaseModel):
    playlist_id: str
    title: str
    reason: str
    tags: list[str]


class PlaylistRecommendationResponse(BaseModel):
    date: str
    holiday: str | None
    recommendations: list[PlaylistRecommendation]


class SongRecommendationOut(BaseModel):
    song_id: str
    title: str
    artist: str
    genre: str
    score: float
    score_breakdown: dict[str, float]


class HybridRecommendationResponse(BaseModel):
    date: str
    holiday: str | None
    location: str | None
    model_backend: str
    recommendations: list[SongRecommendationOut]


class AudioAnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    genre: str = Field(alias="Genre")
    qenet_mode: str = Field(alias="Qenet Mode")
    tempo: float = Field(alias="Tempo")


class HolidayRuleBase(BaseModel):
    key: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    eth_month: int = Field(..., ge=1, le=13)
    eth_day: int = Field(..., ge=1, le=30)
    recommendations: list[PlaylistRecommendation]
    is_active: bool = True


class HolidayRuleCreate(HolidayRuleBase):
    pass


class HolidayRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    eth_month: int | None = Field(default=None, ge=1, le=13)
    eth_day: int | None = Field(default=None, ge=1, le=30)
    recommendations: list[PlaylistRecommendation] | None = None
    is_active: bool | None = None


class HolidayRuleOut(HolidayRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
