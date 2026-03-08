from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

import schemas

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Ethiopian calendar epoch in JDN.
ETH_EPOCH = 1724221


def _gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def _jdn_to_gregorian(jdn: int) -> tuple[int, int, int]:
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def _ethiopian_to_jdn(year: int, month: int, day: int) -> int:
    if month < 1 or month > 13:
        raise ValueError("Ethiopian month must be between 1 and 13")
    max_day = 30 if month <= 12 else (6 if year % 4 == 3 else 5)
    if day < 1 or day > max_day:
        raise ValueError("Invalid day for Ethiopian month")
    return ETH_EPOCH - 1 + 365 * (year - 1) + (year - 1) // 4 + 30 * (month - 1) + day


def _jdn_to_ethiopian(jdn: int) -> tuple[int, int, int]:
    # Start from a safe approximation, then adjust using exact year boundaries.
    year = (4 * (jdn - ETH_EPOCH) + 1463) // 1461
    while _ethiopian_to_jdn(year + 1, 1, 1) <= jdn:
        year += 1
    while _ethiopian_to_jdn(year, 1, 1) > jdn:
        year -= 1

    day_of_year = jdn - _ethiopian_to_jdn(year, 1, 1)
    month = day_of_year // 30 + 1
    day = day_of_year % 30 + 1
    return year, month, day


def _gregorian_to_ethiopian(year: int, month: int, day: int) -> tuple[int, int, int]:
    jdn = _gregorian_to_jdn(year, month, day)
    return _jdn_to_ethiopian(jdn)


def _ethiopian_to_gregorian(year: int, month: int, day: int) -> tuple[int, int, int]:
    jdn = _ethiopian_to_jdn(year, month, day)
    return _jdn_to_gregorian(jdn)


@router.get("/ethiopian-now", response_model=schemas.EthiopianDateOut)
def ethiopian_now():
    now = datetime.now(timezone.utc).date()
    year, month, day = _gregorian_to_ethiopian(now.year, now.month, now.day)
    return {"year": year, "month": month, "day": day}


@router.post("/to-ethiopian", response_model=schemas.EthiopianDateOut)
def to_ethiopian(payload: schemas.GregorianDateIn):
    try:
        year, month, day = _gregorian_to_ethiopian(
            payload.year, payload.month, payload.day
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"year": year, "month": month, "day": day}


@router.post("/to-gregorian", response_model=schemas.GregorianDateIn)
def to_gregorian(payload: schemas.EthiopianDateIn):
    try:
        year, month, day = _ethiopian_to_gregorian(
            payload.year, payload.month, payload.day
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"year": year, "month": month, "day": day}
