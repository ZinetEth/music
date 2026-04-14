from sqlalchemy.orm import Session

from app import models


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> models.User | None:
        return self.db.query(models.User).filter(models.User.id == user_id).first()

    def get_by_identity(
        self,
        *,
        telegram_id: str | None = None,
        email: str | None = None,
    ) -> models.User | None:
        if telegram_id:
            return self.db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
        if email:
            return self.db.query(models.User).filter(models.User.email == email).first()
        return None

    def list_ids(self) -> list[int]:
        return [user_id for (user_id,) in self.db.query(models.User.id).all()]

    def list_peers(self, user_id: int) -> list[models.User]:
        return self.db.query(models.User).filter(models.User.id != user_id).all()

    def save(self, user: models.User) -> models.User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
