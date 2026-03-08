from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import crud
import schemas
from database import get_db

router = APIRouter(tags=["core"])


@router.post("/register-device", response_model=schemas.RegisterDeviceResponse)
def register_device(
    payload: schemas.DeviceRegister,
    request: Request,
    db: Session = Depends(get_db),
):
    telegram_detected = crud.is_telegram_request(payload.telegram, dict(request.headers))
    user = crud.create_user(db, payload, telegram_detected)
    return {"user_id": user.id, "device_class": user.device_class}


@router.get("/can-play/{song_id}/{user_id}", response_model=schemas.CanPlayResponse)
def can_play(song_id: str, user_id: int, db: Session = Depends(get_db)):
    allowed = crud.can_user_play_song(db, song_id, user_id)
    return {"allowed": allowed}


@router.get("/premium-songs", response_model=list[str])
def premium_songs(db: Session = Depends(get_db)):
    return crud.list_premium_song_ids(db)


@router.get("/stream-policy/{user_id}", response_model=schemas.StreamPolicyResponse)
def stream_policy(user_id: int, db: Session = Depends(get_db)):
    try:
        return crud.get_stream_policy(db, user_id)
    except ValueError as exc:
        if str(exc) == "user_not_found":
            raise HTTPException(status_code=404, detail="User not found") from exc
        raise
