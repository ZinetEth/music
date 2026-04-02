import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.core.settings import get_settings
from app.db import get_db
from app.services import crud

router = APIRouter(prefix="/admin/holidays", tags=["admin-holidays"])

settings = get_settings()


def require_admin(x_admin_key: str | None = Header(default=None)):
    if not x_admin_key or not secrets.compare_digest(
        x_admin_key, settings.admin_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )


@router.get(
    "",
    response_model=list[schemas.HolidayRuleOut],
    dependencies=[Depends(require_admin)],
)
def list_rules(db: Session = Depends(get_db)):
    return crud.list_holiday_rules(db)


@router.post(
    "",
    response_model=schemas.HolidayRuleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_rule(payload: schemas.HolidayRuleCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_holiday_rule(db, payload)
    except ValueError as exc:
        if str(exc) == "holiday_key_exists":
            raise HTTPException(
                status_code=409, detail="Holiday key already exists"
            ) from exc
        raise


@router.put(
    "/{rule_id}",
    response_model=schemas.HolidayRuleOut,
    dependencies=[Depends(require_admin)],
)
def update_rule(
    rule_id: int,
    payload: schemas.HolidayRuleUpdate,
    db: Session = Depends(get_db),
):
    try:
        return crud.update_holiday_rule(db, rule_id, payload)
    except ValueError as exc:
        if str(exc) == "holiday_not_found":
            raise HTTPException(
                status_code=404, detail="Holiday rule not found"
            ) from exc
        raise
