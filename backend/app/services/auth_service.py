from fastapi import Request
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import create_access_token
from app.repositories.user_repo import UserRepository
from app.services import crud


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register_device(
        self,
        payload: schemas.DeviceRegister,
        request: Request,
    ) -> schemas.RegisterDeviceResponse:
        telegram_detected = crud.is_telegram_request(payload.telegram, dict(request.headers))
        existing = self.users.get_by_identity(
            telegram_id=payload.telegram_id,
            email=payload.email,
        )

        if existing is not None:
            existing.device_class = crud.detect_device_class(payload.user_agent)
            existing.is_telegram_user = telegram_detected
            user = self.users.save(existing)
        else:
            user = models.User(
                telegram_id=payload.telegram_id,
                email=payload.email,
                device_class=crud.detect_device_class(payload.user_agent),
                is_telegram_user=telegram_detected,
                taste_vector=crud._empty_taste_vector_dict(),
            )
            user = self.users.save(user)

        return schemas.RegisterDeviceResponse(
            access_token=create_access_token(user.id),
            device_class=user.device_class,
            token_type="bearer",
            user_id=user.id,
        )

