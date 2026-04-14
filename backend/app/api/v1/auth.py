from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register-device", response_model=schemas.RegisterDeviceResponse)
def register_device(
    payload: schemas.DeviceRegister,
    request: Request,
    db: Session = Depends(get_db),
):
    return AuthService(db).register_device(payload, request)

