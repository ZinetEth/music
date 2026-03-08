from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import models
import schemas


def utc_now():
    return datetime.now(timezone.utc)


def detect_device_class(user_agent: str) -> schemas.DeviceClass:
    ua = user_agent.lower()
    lite_keywords = ("tecno", "itel", "low ram", "android go")
    high_keywords = ("iphone", "pixel", "ultra", "pro max", "flagship")

    if any(keyword in ua for keyword in lite_keywords):
        return "lite"
    if any(keyword in ua for keyword in high_keywords):
        return "high"
    return "standard"


def is_telegram_request(telegram_flag: bool, headers: dict[str, str]) -> bool:
    if telegram_flag:
        return True

    lowered_headers = {k.lower(): v for k, v in headers.items()}
    telegram_header_keys = (
        "x-telegram-init-data",
        "x-telegram-webapp",
        "x-telegram-platform",
    )
    if any(key in lowered_headers for key in telegram_header_keys):
        return True

    user_agent = lowered_headers.get("user-agent", "").lower()
    return "telegram" in user_agent


def create_user(
    db: Session,
    payload: schemas.DeviceRegister,
    telegram_detected: bool,
) -> models.User:
    user = models.User(
        telegram_id=payload.telegram_id,
        email=payload.email,
        device_class=detect_device_class(payload.user_agent),
        is_telegram_user=telegram_detected,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def can_user_play_song(db: Session, song_id: str, user_id: int) -> bool:
    premium = (
        db.query(models.PremiumContent)
        .filter(
            models.PremiumContent.navidrome_song_id == song_id,
            models.PremiumContent.requires_subscription.is_(True),
        )
        .first()
    )
    if not premium:
        return True

    now = utc_now()
    active_sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.user_id == user_id,
            models.Subscription.status == "active",
            models.Subscription.expires_at > now,
        )
        .first()
    )
    return active_sub is not None


def list_premium_song_ids(db: Session) -> list[str]:
    rows = (
        db.query(models.PremiumContent.navidrome_song_id)
        .filter(models.PremiumContent.requires_subscription.is_(True))
        .all()
    )
    return [song_id for (song_id,) in rows]


def create_marketplace_listing(
    db: Session, payload: schemas.SellPlaylistRequest
) -> models.PlaylistMarketplace:
    listing = models.PlaylistMarketplace(
        playlist_id=payload.playlist_id,
        seller_id=payload.seller_id,
        price=payload.price,
        currency=payload.currency,
        is_public=payload.is_public,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def list_public_marketplace_items(db: Session) -> list[models.PlaylistMarketplace]:
    return (
        db.query(models.PlaylistMarketplace)
        .filter(models.PlaylistMarketplace.is_public.is_(True))
        .all()
    )


def buy_playlist(
    db: Session, payload: schemas.BuyPlaylistRequest
) -> tuple[models.PlaylistMarketplace, models.PlaylistPurchase]:
    listing = (
        db.query(models.PlaylistMarketplace)
        .filter(
            models.PlaylistMarketplace.playlist_id == payload.playlist_id,
            models.PlaylistMarketplace.is_public.is_(True),
        )
        .first()
    )
    if not listing:
        raise ValueError("playlist_not_found")

    purchase = models.PlaylistPurchase(
        playlist_listing_id=listing.id,
        buyer_id=payload.buyer_id,
    )
    listing.sales_count += 1
    db.add(purchase)
    db.commit()
    db.refresh(listing)
    db.refresh(purchase)
    return listing, purchase


def create_payment(db: Session, payload: schemas.PaymentCreateRequest) -> models.Payment:
    payment = models.Payment(
        user_id=payload.user_id,
        amount=payload.amount,
        method=payload.method,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def confirm_payment_and_activate_subscription(
    db: Session, payment_id: int
) -> tuple[models.Payment, models.Subscription]:
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise ValueError("payment_not_found")

    if payment.status != "confirmed":
        payment.status = "confirmed"

    expires_at = utc_now() + timedelta(days=30)
    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == payment.user_id)
        .order_by(models.Subscription.id.desc())
        .first()
    )
    if not subscription:
        subscription = models.Subscription(
            user_id=payment.user_id,
            status="active",
            expires_at=expires_at,
        )
        db.add(subscription)
    else:
        subscription.status = "active"
        subscription.expires_at = expires_at

    db.commit()
    db.refresh(payment)
    db.refresh(subscription)
    return payment, subscription


def get_stream_policy(db: Session, user_id: int) -> dict[str, int | str]:
    user = get_user(db, user_id)
    if not user:
        raise ValueError("user_not_found")

    bitrate_map = {
        "lite": 96,
        "standard": 192,
        "high": 320,
    }
    max_bitrate = bitrate_map.get(user.device_class, 192)

    return {"device_class": user.device_class, "maxBitrate": max_bitrate}


def list_holiday_rules(db: Session) -> list[models.HolidayRule]:
    return db.query(models.HolidayRule).order_by(models.HolidayRule.id.asc()).all()


def list_active_holiday_rules(db: Session) -> list[models.HolidayRule]:
    return (
        db.query(models.HolidayRule)
        .filter(models.HolidayRule.is_active.is_(True))
        .order_by(models.HolidayRule.id.asc())
        .all()
    )


def get_holiday_rule_by_key(db: Session, key: str) -> models.HolidayRule | None:
    return db.query(models.HolidayRule).filter(models.HolidayRule.key == key).first()


def create_holiday_rule(
    db: Session, payload: schemas.HolidayRuleCreate
) -> models.HolidayRule:
    if get_holiday_rule_by_key(db, payload.key):
        raise ValueError("holiday_key_exists")

    rule = models.HolidayRule(
        key=payload.key,
        name=payload.name,
        eth_month=payload.eth_month,
        eth_day=payload.eth_day,
        recommendations=[item.model_dump() for item in payload.recommendations],
        is_active=payload.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_holiday_rule(
    db: Session, rule_id: int, payload: schemas.HolidayRuleUpdate
) -> models.HolidayRule:
    rule = db.query(models.HolidayRule).filter(models.HolidayRule.id == rule_id).first()
    if not rule:
        raise ValueError("holiday_not_found")

    data = payload.model_dump(exclude_unset=True)
    if "recommendations" in data and data["recommendations"] is not None:
        rule.recommendations = [item.model_dump() for item in data["recommendations"]]
        del data["recommendations"]

    for key, value in data.items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)
    return rule
