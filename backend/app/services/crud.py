from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app import models, schemas
from app.core.recommendation_catalog import SONG_CATALOG
from app.services.recommender_engine import (
    PersonalizedRecommender,
    TasteVector,
    TrendingEngine,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


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


def ensure_seed_data(db: Session) -> None:
    existing_song_ids = {
        song_id
        for (song_id,) in db.query(models.LibrarySong.navidrome_song_id).all()
    }
    existing_playlist_ids = {
        playlist_id
        for (playlist_id,) in db.query(models.PlaylistSocialSignal.playlist_id).all()
    }

    playlist_groups: dict[str, list[dict]] = defaultdict(list)
    for index, item in enumerate(SONG_CATALOG, start=1):
        song_id = item["navidrome_song_id"]
        if song_id not in existing_song_ids:
            song = models.LibrarySong(
                navidrome_song_id=song_id,
                title=item["title"],
                artist=item["artist"],
                genre=item["genre"],
                country=item.get("country"),
                language=item.get("language"),
                qenet_mode=item.get("qenet_mode"),
                release_date=item.get("release_date"),
                tempo=float(item.get("tempo", 0)),
                duration=float(item.get("duration", 0)),
                extracted_features=item.get("extracted_features", {}),
                playlist_id=item.get("playlist_id"),
                play_count_7d=int(item.get("play_count_7d", 0)),
                like_count_7d=int(item.get("like_count_7d", 0)),
                skip_rate=float(item.get("skip_rate", 0)),
                cover_art_path=f"/protected/art/{song_id}.jpg",
                stream_path=f"/protected/audio/{song_id}.mp3",
                is_premium=bool(item.get("is_premium", False)),
            )
            db.add(song)

        playlist_id = item.get("playlist_id")
        if playlist_id:
            playlist_groups[playlist_id].append(item)
            if playlist_id not in existing_playlist_ids:
                signal = models.PlaylistSocialSignal(
                    playlist_id=playlist_id,
                    title=item.get("playlist_title", item["title"]),
                    creator_name=item.get("creator_name", item["artist"]),
                    artist_name=item["artist"],
                    artist_verified=bool(item.get("artist_verified", index % 2 == 1)),
                    save_count=int(item.get("save_count", 30 + (index * 3))),
                    share_count=int(item.get("share_count", 12 + index)),
                    region=item.get("country"),
                    preview_song_id=song_id,
                    cover_art_path=f"/protected/art/{playlist_id}.jpg",
                    internal_stream_path=f"/internal/playlists/{playlist_id}.m3u8",
                    internal_art_path=f"/internal/art/{playlist_id}.jpg",
                )
                db.add(signal)

        if item.get("is_premium"):
            premium_row = (
                db.query(models.PremiumContent)
                .filter(models.PremiumContent.navidrome_song_id == song_id)
                .first()
            )
            if premium_row is None:
                db.add(
                    models.PremiumContent(
                        navidrome_song_id=song_id,
                        requires_subscription=True,
                    )
                )

    existing_listings = {
        playlist_id
        for (playlist_id,) in db.query(models.PlaylistMarketplace.playlist_id).all()
    }
    existing_song_listings = {
        song_id for (song_id,) in db.query(models.SongMarketplace.song_id).all()
    }
    default_seller = db.query(models.User).filter(models.User.id == 1).first()
    if default_seller is None:
        default_seller = models.User(
            email="demo@music.local",
            device_class="standard",
            is_telegram_user=False,
        )
        db.add(default_seller)
        db.flush()

    for playlist_id, items in playlist_groups.items():
        if playlist_id in existing_listings:
            continue
        lead = items[0]
        db.add(
            models.PlaylistMarketplace(
                playlist_id=playlist_id,
                seller_id=default_seller.id,
                price=float(lead.get("playlist_price", 79)),
                currency="ETB",
                sales_count=int(lead.get("sales_count", 5)),
                is_public=True,
            )
        )

    for index, item in enumerate(SONG_CATALOG, start=1):
        song_id = item["navidrome_song_id"]
        if song_id in existing_song_listings:
            continue
        db.add(
            models.SongMarketplace(
                song_id=song_id,
                seller_id=default_seller.id,
                price=float(item.get("song_price", 39 if item.get("is_premium") else 19)),
                currency="ETB",
                sales_count=int(item.get("song_sales_count", item.get("sales_count", max(2, index)))),
                is_public=True,
            )
        )

    db.commit()


def create_user(
    db: Session,
    payload: schemas.DeviceRegister,
    telegram_detected: bool,
) -> models.User:
    existing = None
    if payload.telegram_id:
        existing = (
            db.query(models.User)
            .filter(models.User.telegram_id == payload.telegram_id)
            .first()
        )
    elif payload.email:
        existing = (
            db.query(models.User)
            .filter(models.User.email == payload.email)
            .first()
        )

    if existing:
        existing.device_class = detect_device_class(payload.user_agent)
        existing.is_telegram_user = telegram_detected
        db.commit()
        db.refresh(existing)
        return existing

    user = models.User(
        telegram_id=payload.telegram_id,
        email=payload.email,
        device_class=detect_device_class(payload.user_agent),
        is_telegram_user=telegram_detected,
        taste_vector=_empty_taste_vector_dict(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_or_create_song_from_event(
    db: Session, payload: schemas.PlaybackEventIn
) -> models.LibrarySong:
    song = (
        db.query(models.LibrarySong)
        .filter(models.LibrarySong.navidrome_song_id == payload.song_id)
        .first()
    )
    if song:
        song.title = payload.title
        song.artist = payload.artist
        song.genre = payload.genre
        song.country = payload.country
        song.language = payload.language
        song.qenet_mode = payload.qenet_mode
        song.release_date = payload.release_date
        song.tempo = payload.tempo
        song.duration = payload.duration
        song.extracted_features = payload.extracted_features
        song.playlist_id = payload.playlist_id
        song.updated_at = utc_now()
        return song

    song = models.LibrarySong(
        navidrome_song_id=payload.song_id,
        title=payload.title,
        artist=payload.artist,
        genre=payload.genre,
        country=payload.country,
        language=payload.language,
        qenet_mode=payload.qenet_mode,
        release_date=payload.release_date,
        tempo=payload.tempo,
        duration=payload.duration,
        extracted_features=payload.extracted_features,
        playlist_id=payload.playlist_id,
        cover_art_path=f"/protected/art/{payload.song_id}.jpg",
        stream_path=f"/protected/audio/{payload.song_id}.mp3",
    )
    db.add(song)
    db.flush()
    return song


def _engagement_weight(payload: schemas.PlaybackEventIn) -> float:
    ratio = min(max(payload.completed_ratio, 0.0), 2.0)
    base = max(ratio, 0.1)
    if payload.is_looped:
        base += 0.35
    if payload.skipped:
        base *= 0.35
    return round(base, 4)


def _feature_signature(features: dict) -> dict[str, float]:
    acoustic_signature: dict[str, float] = {}
    for key in ("energy", "danceability", "valence", "spectral_centroid_mean"):
        value = features.get(key)
        if isinstance(value, int | float):
            acoustic_signature[key] = float(value)
    return acoustic_signature


def _empty_taste_vector_dict() -> dict:
    return {
        "qenet_mode_affinity": {},
        "genre_affinity": {},
        "average_tempo": 0.0,
        "acoustic_signature": {},
    }


def _to_taste_vector(data: dict | None) -> TasteVector:
    safe = data or _empty_taste_vector_dict()
    return TasteVector(
        qenet_mode_affinity={
            key: float(value)
            for key, value in safe.get("qenet_mode_affinity", {}).items()
        },
        genre_affinity={
            key: float(value) for key, value in safe.get("genre_affinity", {}).items()
        },
        average_tempo=float(safe.get("average_tempo", 0.0)),
        acoustic_signature={
            key: float(value)
            for key, value in safe.get("acoustic_signature", {}).items()
        },
    )


def _taste_vector_schema(vector: TasteVector) -> schemas.TasteVectorOut:
    return schemas.TasteVectorOut(
        qenet_mode_affinity=vector.qenet_mode_affinity,
        genre_affinity=vector.genre_affinity,
        average_tempo=round(vector.average_tempo, 2),
        acoustic_signature={
            key: round(value, 4) for key, value in vector.acoustic_signature.items()
        },
    )


def refresh_user_taste_vector(db: Session, user_id: int) -> TasteVector:
    events = (
        db.query(models.PlaybackEvent)
        .join(models.LibrarySong, models.LibrarySong.id == models.PlaybackEvent.song_id)
        .filter(models.PlaybackEvent.user_id == user_id)
        .order_by(models.PlaybackEvent.occurred_at.desc())
        .all()
    )

    if not events:
        user = get_user(db, user_id)
        if user:
            user.taste_vector = _empty_taste_vector_dict()
            db.commit()
        return _to_taste_vector(None)

    qenet_scores: Counter[str] = Counter()
    genre_scores: Counter[str] = Counter()
    acoustic_totals: defaultdict[str, float] = defaultdict(float)
    total_weight = 0.0
    weighted_tempo = 0.0

    for event in events:
        song = event.song
        weight = max(float(event.weight or 0), 0.1)
        total_weight += weight
        weighted_tempo += (song.tempo or 0.0) * weight

        if song.qenet_mode:
            qenet_scores[song.qenet_mode] += weight
        if song.genre:
            genre_scores[song.genre] += weight

        signature = _feature_signature(song.extracted_features or {})
        for key, value in signature.items():
            acoustic_totals[key] += value * weight

    def normalize(counter: Counter[str]) -> dict[str, float]:
        if total_weight <= 0:
            return {}
        return {
            key: round(value / total_weight, 4)
            for key, value in counter.items()
        }

    acoustic_signature = {
        key: round(value / total_weight, 4)
        for key, value in acoustic_totals.items()
        if total_weight > 0
    }
    vector = TasteVector(
        qenet_mode_affinity=normalize(qenet_scores),
        genre_affinity=normalize(genre_scores),
        average_tempo=round(weighted_tempo / total_weight, 4) if total_weight else 0.0,
        acoustic_signature=acoustic_signature,
    )

    user = get_user(db, user_id)
    if user:
        user.taste_vector = _empty_taste_vector_dict() | {
            "qenet_mode_affinity": vector.qenet_mode_affinity,
            "genre_affinity": vector.genre_affinity,
            "average_tempo": vector.average_tempo,
            "acoustic_signature": vector.acoustic_signature,
        }
        db.commit()

    return vector


def record_playback_event(
    db: Session, payload: schemas.PlaybackEventIn
) -> schemas.PlaybackEventResponse:
    user = get_user(db, payload.user_id)
    if not user:
        raise ValueError("user_not_found")

    song = get_or_create_song_from_event(db, payload)
    weight = _engagement_weight(payload)
    event = models.PlaybackEvent(
        user_id=payload.user_id,
        song_id=song.id,
        location=payload.location,
        completed_ratio=payload.completed_ratio,
        played_seconds=payload.played_seconds,
        is_looped=payload.is_looped,
        skipped=payload.skipped,
        weight=weight,
    )
    db.add(event)

    song.play_count_7d += 1
    if payload.completed_ratio >= 0.85:
        song.like_count_7d += 1
    if payload.skipped:
        total = max(song.play_count_7d, 1)
        skipped_events = (
            db.query(models.PlaybackEvent)
            .filter(
                models.PlaybackEvent.song_id == song.id,
                models.PlaybackEvent.skipped.is_(True),
            )
            .count()
        )
        song.skip_rate = round((skipped_events + 1) / total, 4)

    db.commit()
    db.refresh(event)
    db.refresh(song)

    vector = refresh_user_taste_vector(db, payload.user_id)
    return schemas.PlaybackEventResponse(
        recorded=True,
        user_id=payload.user_id,
        song_id=payload.song_id,
        updated_taste_vector=_taste_vector_schema(vector),
    )


def can_user_play_song(db: Session, song_id: str, user_id: int) -> bool:
    if has_song_access(db, song_id, user_id):
        return True

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

    status = get_subscription_status(db, user_id)
    return status.subscribed


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

    signal = (
        db.query(models.PlaylistSocialSignal)
        .filter(models.PlaylistSocialSignal.playlist_id == payload.playlist_id)
        .first()
    )
    if signal is None:
        seller = get_user(db, payload.seller_id)
        creator_name = (
            seller.email
            if seller and seller.email
            else f"Creator {payload.seller_id}"
        )
        db.add(
            models.PlaylistSocialSignal(
                playlist_id=payload.playlist_id,
                title=f"Playlist {payload.playlist_id}",
                creator_name=creator_name,
                artist_name=creator_name,
                artist_verified=False,
                internal_stream_path=f"/internal/playlists/{payload.playlist_id}.m3u8",
                internal_art_path=f"/internal/art/{payload.playlist_id}.jpg",
                cover_art_path=f"/protected/art/{payload.playlist_id}.jpg",
            )
        )

    db.commit()
    db.refresh(listing)
    return listing


def create_song_marketplace_listing(
    db: Session, payload: schemas.SellSongRequest
) -> models.SongMarketplace:
    song = (
        db.query(models.LibrarySong)
        .filter(models.LibrarySong.navidrome_song_id == payload.song_id)
        .first()
    )
    if song is None:
        raise ValueError("song_not_found")

    listing = (
        db.query(models.SongMarketplace)
        .filter(models.SongMarketplace.song_id == payload.song_id)
        .first()
    )
    if listing is None:
        listing = models.SongMarketplace(
            song_id=payload.song_id,
            seller_id=payload.seller_id,
            price=payload.price,
            currency=payload.currency,
            is_public=payload.is_public,
        )
        db.add(listing)
    else:
        listing.seller_id = payload.seller_id
        listing.price = payload.price
        listing.currency = payload.currency
        listing.is_public = payload.is_public

    db.commit()
    db.refresh(listing)
    return listing


def _marketplace_projection(
    listing: models.PlaylistMarketplace,
    signal: models.PlaylistSocialSignal | None,
) -> schemas.MarketplacePlaylistOut:
    save_count = signal.save_count if signal else 0
    share_count = signal.share_count if signal else 0
    social_denominator = max(save_count + share_count + listing.sales_count, 1)
    save_rate = save_count / social_denominator
    social_score = (
        (listing.sales_count * 1.8)
        + (save_count * 1.2)
        + (share_count * 0.6)
        + (20 if signal and signal.artist_verified else 0)
    )

    return schemas.MarketplacePlaylistOut(
        playlist_id=listing.playlist_id,
        title=signal.title if signal else listing.playlist_id,
        creator_name=signal.creator_name if signal else f"Seller {listing.seller_id}",
        artist_name=signal.artist_name if signal else None,
        artist_verified=signal.artist_verified if signal else False,
        price=listing.price,
        currency=listing.currency,
        sales_count=listing.sales_count,
        save_count=save_count,
        share_count=share_count,
        save_rate=round(save_rate, 4),
        social_score=round(social_score, 4),
        region=signal.region if signal else None,
        preview_song_id=signal.preview_song_id if signal else None,
        cover_art_path=signal.cover_art_path if signal else None,
    )


def list_public_marketplace_items(db: Session) -> list[schemas.MarketplacePlaylistOut]:
    listings = (
        db.query(models.PlaylistMarketplace)
        .filter(models.PlaylistMarketplace.is_public.is_(True))
        .all()
    )
    signals = {
        signal.playlist_id: signal
        for signal in db.query(models.PlaylistSocialSignal).all()
    }
    projected = [
        _marketplace_projection(listing, signals.get(listing.playlist_id))
        for listing in listings
    ]
    return sorted(projected, key=lambda item: item.social_score, reverse=True)


def list_public_song_marketplace_items(db: Session) -> list[schemas.MarketplaceSongOut]:
    listings = (
        db.query(models.SongMarketplace)
        .filter(models.SongMarketplace.is_public.is_(True))
        .all()
    )
    songs = {
        song.navidrome_song_id: song for song in db.query(models.LibrarySong).all()
    }
    projected: list[schemas.MarketplaceSongOut] = []

    for listing in listings:
        song = songs.get(listing.song_id)
        if song is None:
            continue
        projected.append(
            schemas.MarketplaceSongOut(
                song_id=song.navidrome_song_id,
                title=song.title,
                artist=song.artist,
                genre=song.genre,
                price=listing.price,
                currency=listing.currency,
                sales_count=listing.sales_count,
                play_count_7d=song.play_count_7d,
                like_count_7d=song.like_count_7d,
                cover_art_path=song.cover_art_path,
                is_premium=song.is_premium,
            )
        )

    return sorted(
        projected,
        key=lambda item: (item.sales_count * 2) + item.like_count_7d + item.play_count_7d,
        reverse=True,
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

    existing_purchase = (
        db.query(models.PlaylistPurchase)
        .filter(
            models.PlaylistPurchase.playlist_listing_id == listing.id,
            models.PlaylistPurchase.buyer_id == payload.buyer_id,
        )
        .first()
    )
    if existing_purchase:
        return listing, existing_purchase

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


def buy_song(
    db: Session, payload: schemas.BuySongRequest
) -> tuple[models.SongMarketplace, models.SongPurchase]:
    listing = (
        db.query(models.SongMarketplace)
        .filter(
            models.SongMarketplace.song_id == payload.song_id,
            models.SongMarketplace.is_public.is_(True),
        )
        .first()
    )
    if not listing:
        raise ValueError("song_not_found")

    existing_purchase = (
        db.query(models.SongPurchase)
        .filter(
            models.SongPurchase.song_listing_id == listing.id,
            models.SongPurchase.buyer_id == payload.buyer_id,
        )
        .first()
    )
    if existing_purchase:
        return listing, existing_purchase

    purchase = models.SongPurchase(
        song_listing_id=listing.id,
        buyer_id=payload.buyer_id,
    )
    listing.sales_count += 1
    db.add(purchase)
    db.commit()
    db.refresh(listing)
    db.refresh(purchase)
    return listing, purchase


def save_playlist(
    db: Session, payload: schemas.SavePlaylistRequest
) -> schemas.SavePlaylistResponse:
    existing = (
        db.query(models.UserPlaylistSave)
        .filter(
            models.UserPlaylistSave.user_id == payload.user_id,
            models.UserPlaylistSave.playlist_id == payload.playlist_id,
        )
        .first()
    )
    signal = (
        db.query(models.PlaylistSocialSignal)
        .filter(models.PlaylistSocialSignal.playlist_id == payload.playlist_id)
        .first()
    )
    if signal is None:
        raise ValueError("playlist_not_found")

    if existing is None:
        db.add(
            models.UserPlaylistSave(
                user_id=payload.user_id,
                playlist_id=payload.playlist_id,
            )
        )
        signal.save_count += 1
        db.commit()
        db.refresh(signal)

    return schemas.SavePlaylistResponse(
        playlist_id=payload.playlist_id,
        save_count=signal.save_count,
        saved=True,
    )


def secure_playlist_access(
    db: Session, playlist_id: str, user_id: int
) -> schemas.SecurePlaylistAccessResponse:
    listing = (
        db.query(models.PlaylistMarketplace)
        .filter(models.PlaylistMarketplace.playlist_id == playlist_id)
        .first()
    )
    signal = (
        db.query(models.PlaylistSocialSignal)
        .filter(models.PlaylistSocialSignal.playlist_id == playlist_id)
        .first()
    )
    if listing is None or signal is None:
        raise ValueError("playlist_not_found")

    authorized = listing.seller_id == user_id
    if not authorized:
        authorized = (
            db.query(models.PlaylistPurchase)
            .filter(
                models.PlaylistPurchase.playlist_listing_id == listing.id,
                models.PlaylistPurchase.buyer_id == user_id,
            )
            .first()
            is not None
        )

    return schemas.SecurePlaylistAccessResponse(
        playlist_id=playlist_id,
        authorized=authorized,
        x_accel_redirect=signal.internal_stream_path if authorized else None,
        art_redirect=signal.internal_art_path if authorized else None,
        stream_path=signal.internal_stream_path if authorized else None,
        art_path=signal.internal_art_path if authorized else None,
    )


def has_song_access(db: Session, song_id: str, user_id: int) -> bool:
    listing = (
        db.query(models.SongMarketplace)
        .filter(models.SongMarketplace.song_id == song_id)
        .first()
    )
    if listing is None:
        return False

    if listing.seller_id == user_id:
        return True

    return (
        db.query(models.SongPurchase)
        .filter(
            models.SongPurchase.song_listing_id == listing.id,
            models.SongPurchase.buyer_id == user_id,
        )
        .first()
        is not None
    )


def secure_song_access(
    db: Session, song_id: str, user_id: int
) -> schemas.SecureSongAccessResponse:
    song = (
        db.query(models.LibrarySong)
        .filter(models.LibrarySong.navidrome_song_id == song_id)
        .first()
    )
    if song is None:
        raise ValueError("song_not_found")

    authorized = has_song_access(db, song_id, user_id) or can_user_play_song(
        db, song_id, user_id
    )
    return schemas.SecureSongAccessResponse(
        song_id=song_id,
        authorized=authorized,
        stream_path=song.stream_path if authorized else None,
        art_path=song.cover_art_path if authorized else None,
    )


def create_payment(
    db: Session, payload: schemas.PaymentCreateRequest
) -> models.Payment:
    payment = models.Payment(
        user_id=payload.user_id,
        amount=payload.amount,
        method=payload.method,
        payment_type=payload.payment_type,
        playlist_id=payload.playlist_id,
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


def get_subscription_status(
    db: Session, user_id: int
) -> schemas.SubscriptionCheckResponse:
    now = utc_now()
    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == user_id)
        .order_by(models.Subscription.id.desc())
        .first()
    )
    if (
        subscription
        and subscription.status == "active"
        and subscription.expires_at > now
    ):
        return schemas.SubscriptionCheckResponse(
            subscribed=True,
            status="active",
            expires_at=subscription.expires_at,
        )
    return schemas.SubscriptionCheckResponse(
        subscribed=False,
        status="expired",
        expires_at=subscription.expires_at if subscription else None,
    )


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


def _song_rows(db: Session) -> list[models.LibrarySong]:
    return db.query(models.LibrarySong).all()


def _recent_playback_events(
    db: Session,
    hours: int = 168,
) -> list[models.PlaybackEvent]:
    cutoff = utc_now() - timedelta(hours=hours)
    return (
        db.query(models.PlaybackEvent)
        .filter(models.PlaybackEvent.occurred_at >= cutoff)
        .all()
    )


def _user_heard_song_ids(db: Session, user_id: int) -> set[str]:
    rows = (
        db.query(models.LibrarySong.navidrome_song_id)
        .join(
            models.PlaybackEvent,
            models.PlaybackEvent.song_id == models.LibrarySong.id,
        )
        .filter(models.PlaybackEvent.user_id == user_id)
        .all()
    )
    return {song_id for (song_id,) in rows}


def _lookalike_audience(
    db: Session,
    user_id: int,
    vector: TasteVector,
) -> list[schemas.LookalikeUserOut]:
    recommender = PersonalizedRecommender()
    results: list[schemas.LookalikeUserOut] = []
    for user in db.query(models.User).filter(models.User.id != user_id).all():
        other_vector = _to_taste_vector(user.taste_vector)
        similarity = recommender.cosine_similarity(vector, other_vector)
        if similarity > 0:
            results.append(
                schemas.LookalikeUserOut(
                    user_id=user.id,
                    similarity=round(similarity, 4),
                )
            )
    return sorted(results, key=lambda item: item.similarity, reverse=True)[:5]


def get_personalized_feed(
    db: Session,
    user_id: int,
    location: str | None,
    limit: int,
) -> schemas.PersonalizedFeedResponse:
    user = get_user(db, user_id)
    if user is None:
        raise ValueError("user_not_found")

    songs = _song_rows(db)
    events = _recent_playback_events(db, hours=24 * 30)
    heard_song_ids = _user_heard_song_ids(db, user_id)
    vector = refresh_user_taste_vector(db, user_id)
    recommender = PersonalizedRecommender()

    ranked = recommender.rank_for_user(
        user_id=user_id,
        songs=songs,
        events=events,
        taste_vector=vector,
        heard_song_ids=heard_song_ids,
        location=location,
        limit=limit,
    )
    lookalikes = _lookalike_audience(db, user_id, vector)

    return schemas.PersonalizedFeedResponse(
        user_id=user_id,
        location=location,
        model_backend="taste_vector_collaborative_v1",
        taste_vector=_taste_vector_schema(vector),
        lookalike_audience=lookalikes,
        recommendations=[
            schemas.SongRecommendationOut(**row) for row in ranked
        ],
    )


def get_trending_feed(
    db: Session, location: str | None, limit: int
) -> schemas.TrendingFeedResponse:
    songs = _song_rows(db)
    events = _recent_playback_events(db, hours=24 * 7)
    playlist_stats = {
        signal.playlist_id: signal
        for signal in db.query(models.PlaylistSocialSignal).all()
    }
    engine = TrendingEngine()
    ranked = engine.rank(
        songs=songs,
        events=events,
        playlist_stats=playlist_stats,
        location=location,
        limit=limit,
    )
    return schemas.TrendingFeedResponse(
        location=location,
        generated_at=utc_now().isoformat(),
        recommendations=[schemas.TrendingSongOut(**row) for row in ranked],
    )


def get_user_profile(db: Session, user_id: int) -> schemas.UserProfileResponse:
    user = get_user(db, user_id)
    if user is None:
        raise ValueError("user_not_found")

    subscription = get_subscription_status(db, user_id)
    vector = refresh_user_taste_vector(db, user_id)
    lookalikes = _lookalike_audience(db, user_id, vector)
    latest_event = (
        db.query(models.PlaybackEvent)
        .filter(models.PlaybackEvent.user_id == user_id)
        .order_by(models.PlaybackEvent.occurred_at.desc())
        .first()
    )
    secure_playlist_ids = [
        listing.playlist_id
        for listing in (
            db.query(models.PlaylistMarketplace)
            .join(
                models.PlaylistPurchase,
                (
                    models.PlaylistPurchase.playlist_listing_id
                    == models.PlaylistMarketplace.id
                ),
                isouter=True,
            )
            .filter(
                (models.PlaylistMarketplace.seller_id == user_id)
                | (models.PlaylistPurchase.buyer_id == user_id)
            )
            .all()
        )
    ]

    return schemas.UserProfileResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        email=user.email,
        device_class=user.device_class,
        is_telegram_user=user.is_telegram_user,
        created_at=user.created_at,
        preferred_location=latest_event.location if latest_event else None,
        active_subscription=subscription.subscribed,
        subscription_status=subscription.status,
        expires_at=subscription.expires_at,
        taste_vector=_taste_vector_schema(vector),
        lookalike_audience=lookalikes,
        recent_playback_count=(
            db.query(models.PlaybackEvent)
            .filter(models.PlaybackEvent.user_id == user_id)
            .count()
        ),
        secure_playlist_ids=sorted(set(secure_playlist_ids)),
    )
