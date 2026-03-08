from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from database import SessionLocal
from models import PremiumContent, Subscription, User


def seed_database(db: Session):
    # Test user
    user = User(
        telegram_id="123456",
        email="test@example.com",
        device_class="lite",
        is_telegram_user=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Active subscription
    subscription = Subscription(
        user_id=user.id,
        status="active",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(subscription)

    # Premium song example
    premium_song = PremiumContent(
        navidrome_song_id="song123",
        requires_subscription=True,
    )
    db.add(premium_song)

    db.commit()
    print("Seed data created.")


if __name__ == "__main__":
    session = SessionLocal()
    try:
        seed_database(session)
    finally:
        session.close()
