from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.holidays import HOLIDAY_RULES
from app.db import SessionLocal
from app.models import (
    HolidayRule,
    MusicMetadata,
    Payment,
    PlaylistMarketplace,
    PlaylistPurchase,
    PremiumContent,
    Subscription,
    User,
    UserPlaybackLog,
)
from app.seeding.fixtures import (
    MOCK_MARKETPLACE_LISTINGS,
    MOCK_MUSIC_METADATA,
    MOCK_PREMIUM_SONG_IDS,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_user(
    db: Session,
    *,
    email: str | None,
    telegram_id: str | None,
    device_class: str,
    is_telegram_user: bool,
) -> User:
    query = db.query(User)
    if email:
        query = query.filter(User.email == email)
    elif telegram_id:
        query = query.filter(User.telegram_id == telegram_id)
    else:
        raise ValueError("email or telegram_id is required")

    existing = query.first()
    if existing:
        existing.device_class = device_class
        existing.is_telegram_user = is_telegram_user
        if telegram_id:
            existing.telegram_id = telegram_id
        db.commit()
        db.refresh(existing)
        return existing

    user = User(
        email=email,
        telegram_id=telegram_id,
        device_class=device_class,
        is_telegram_user=is_telegram_user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_subscription(
    db: Session,
    *,
    user_id: int,
    status: str,
    expires_at: datetime,
) -> Subscription:
    existing = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if existing:
        existing.status = status
        existing.expires_at = expires_at
        db.commit()
        db.refresh(existing)
        return existing

    subscription = Subscription(user_id=user_id, status=status, expires_at=expires_at)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def ensure_premium_content(db: Session, song_ids: list[str]) -> None:
    existing_ids = {
        row[0]
        for row in db.query(PremiumContent.navidrome_song_id)
        .filter(PremiumContent.navidrome_song_id.in_(song_ids))
        .all()
    }

    for song_id in song_ids:
        if song_id in existing_ids:
            continue
        db.add(PremiumContent(navidrome_song_id=song_id, requires_subscription=True))

    db.commit()


def ensure_marketplace_listing(
    db: Session,
    *,
    playlist_id: str,
    seller_id: int,
    price: float,
    currency: str = "ETB",
    sales_count: int = 0,
    is_public: bool = True,
) -> PlaylistMarketplace:
    existing = (
        db.query(PlaylistMarketplace)
        .filter(PlaylistMarketplace.playlist_id == playlist_id)
        .first()
    )
    if existing:
        existing.seller_id = seller_id
        existing.price = price
        existing.currency = currency
        existing.sales_count = sales_count
        existing.is_public = is_public
        db.commit()
        db.refresh(existing)
        return existing

    listing = PlaylistMarketplace(
        playlist_id=playlist_id,
        seller_id=seller_id,
        price=price,
        currency=currency,
        sales_count=sales_count,
        is_public=is_public,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def ensure_purchase(db: Session, *, listing_id: int, buyer_id: int) -> PlaylistPurchase:
    existing = (
        db.query(PlaylistPurchase)
        .filter(
            PlaylistPurchase.playlist_listing_id == listing_id,
            PlaylistPurchase.buyer_id == buyer_id,
        )
        .first()
    )
    if existing:
        return existing

    purchase = PlaylistPurchase(playlist_listing_id=listing_id, buyer_id=buyer_id)
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase


def ensure_payment(
    db: Session,
    *,
    user_id: int,
    amount: float,
    method: str,
    status: str,
) -> Payment:
    existing = (
        db.query(Payment)
        .filter(
            Payment.user_id == user_id,
            Payment.amount == amount,
            Payment.method == method,
        )
        .first()
    )
    if existing:
        existing.status = status
        db.commit()
        db.refresh(existing)
        return existing

    payment = Payment(user_id=user_id, amount=amount, method=method, status=status)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def ensure_holiday_rules(db: Session) -> None:
    for rule in HOLIDAY_RULES:
        existing = db.query(HolidayRule).filter(HolidayRule.key == rule["key"]).first()
        if existing:
            existing.name = rule["name"]
            existing.eth_month = rule["eth_month"]
            existing.eth_day = rule["eth_day"]
            existing.recommendations = rule["recommendations"]
            existing.is_active = True
            continue

        db.add(
            HolidayRule(
                key=rule["key"],
                name=rule["name"],
                eth_month=rule["eth_month"],
                eth_day=rule["eth_day"],
                recommendations=rule["recommendations"],
                is_active=True,
            )
        )

    db.commit()


def ensure_music_metadata(
    db: Session,
    entries: list[dict[str, object]],
) -> list[MusicMetadata]:
    rows: list[MusicMetadata] = []

    for entry in entries:
        existing = (
            db.query(MusicMetadata)
            .filter(MusicMetadata.filename == entry["filename"])
            .first()
        )

        if existing:
            existing.artist = entry["artist"]
            existing.genre = entry["genre"]
            existing.qenet_mode = entry["qenet_mode"]
            existing.tempo = entry["tempo"]
            existing.duration = entry["duration"]
            existing.extracted_features = entry["extracted_features"]
            rows.append(existing)
            continue

        metadata = MusicMetadata(**entry)
        db.add(metadata)
        db.flush()
        rows.append(metadata)

    db.commit()

    for row in rows:
        db.refresh(row)

    return rows


def ensure_playback_log(
    db: Session,
    *,
    user_id: int,
    music_id: int,
    played_seconds: float,
    skipped: bool,
) -> UserPlaybackLog:
    existing = (
        db.query(UserPlaybackLog)
        .filter(
            UserPlaybackLog.user_id == user_id,
            UserPlaybackLog.music_id == music_id,
        )
        .first()
    )
    if existing:
        existing.played_seconds = played_seconds
        existing.skipped = skipped
        existing.timestamp = utc_now()
        db.commit()
        db.refresh(existing)
        return existing

    log = UserPlaybackLog(
        user_id=user_id,
        music_id=music_id,
        played_seconds=played_seconds,
        skipped=skipped,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def seed_database(db: Session) -> None:
    now = utc_now()

    telegram_user = ensure_user(
        db,
        email=None,
        telegram_id="123456",
        device_class="lite",
        is_telegram_user=True,
    )
    premium_user = ensure_user(
        db,
        email="premium@example.com",
        telegram_id=None,
        device_class="high",
        is_telegram_user=False,
    )
    free_user = ensure_user(
        db,
        email="listener@example.com",
        telegram_id=None,
        device_class="standard",
        is_telegram_user=False,
    )

    ensure_subscription(
        db,
        user_id=telegram_user.id,
        status="active",
        expires_at=now + timedelta(days=30),
    )
    ensure_subscription(
        db,
        user_id=premium_user.id,
        status="active",
        expires_at=now + timedelta(days=14),
    )
    ensure_subscription(
        db,
        user_id=free_user.id,
        status="expired",
        expires_at=now - timedelta(days=3),
    )

    ensure_premium_content(db, MOCK_PREMIUM_SONG_IDS)

    seller_map = {
        "premium": premium_user.id,
        "telegram": telegram_user.id,
    }
    seeded_listings = [
        ensure_marketplace_listing(
            db,
            playlist_id=listing["playlist_id"],
            seller_id=seller_map[listing["seller_key"]],
            price=listing["price"],
            currency=listing["currency"],
            sales_count=listing["sales_count"],
        )
        for listing in MOCK_MARKETPLACE_LISTINGS
    ]

    ensure_purchase(db, listing_id=seeded_listings[0].id, buyer_id=telegram_user.id)
    ensure_purchase(db, listing_id=seeded_listings[1].id, buyer_id=free_user.id)

    ensure_payment(
        db,
        user_id=telegram_user.id,
        amount=99.0,
        method="telebirr",
        status="confirmed",
    )
    ensure_payment(
        db,
        user_id=free_user.id,
        amount=49.0,
        method="cbe",
        status="pending",
    )

    ensure_holiday_rules(db)

    metadata_rows = ensure_music_metadata(db, MOCK_MUSIC_METADATA)

    ensure_playback_log(
        db,
        user_id=telegram_user.id,
        music_id=metadata_rows[0].id,
        played_seconds=214.0,
        skipped=False,
    )
    ensure_playback_log(
        db,
        user_id=premium_user.id,
        music_id=metadata_rows[1].id,
        played_seconds=42.0,
        skipped=True,
    )
    ensure_playback_log(
        db,
        user_id=free_user.id,
        music_id=metadata_rows[2].id,
        played_seconds=201.0,
        skipped=False,
    )

    print("Mock data seeded.")


def main() -> None:
    session = SessionLocal()
    try:
        seed_database(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
