from fastapi import APIRouter
from sqlalchemy import text

from app.db import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/live")
def live():
    return {"status": "alive"}


@router.get("/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}

