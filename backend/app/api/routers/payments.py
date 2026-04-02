from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.services import crud

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/create", response_model=schemas.PaymentOut)
def create_payment(
    payload: schemas.PaymentCreateRequest, db: Session = Depends(get_db)
):
    user = crud.get_user(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.create_payment(db, payload)


@router.post("/confirm", response_model=schemas.PaymentConfirmResponse)
def confirm_payment(
    payload: schemas.PaymentConfirmRequest, db: Session = Depends(get_db)
):
    try:
        payment, subscription = crud.confirm_payment_and_activate_subscription(
            db, payload.payment_id
        )
    except ValueError as exc:
        if str(exc) == "payment_not_found":
            raise HTTPException(status_code=404, detail="Payment not found") from exc
        raise

    return {
        "payment_id": payment.id,
        "status": payment.status,
        "subscription_status": subscription.status,
        "expires_at": subscription.expires_at,
    }
