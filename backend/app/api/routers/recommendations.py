from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.api.routers.calendar import _gregorian_to_ethiopian
from app.core.holidays import DEFAULT_RECOMMENDATIONS, HOLIDAY_RULES
from app.core.recommendation_catalog import SONG_CATALOG
from app.db import get_db
from app.services import crud
from app.services.recommender_engine import HybridRecommender, SongCandidate

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _runtime_rules(db: Session) -> list[dict]:
    db_rules = crud.list_active_holiday_rules(db)
    merged: dict[str, dict] = {rule["key"]: dict(rule) for rule in HOLIDAY_RULES}
    for rule in db_rules:
        merged[rule.key] = {
            "key": rule.key,
            "name": rule.name,
            "eth_month": rule.eth_month,
            "eth_day": rule.eth_day,
            "recommendations": rule.recommendations,
        }
    return list(merged.values())


def _build_recommendations(
    holiday: str | None, rules: list[dict]
) -> list[schemas.PlaylistRecommendation]:
    if holiday:
        for rule in rules:
            if rule["key"] == holiday:
                return [
                    schemas.PlaylistRecommendation(**item)
                    for item in rule["recommendations"]
                ]

    return [schemas.PlaylistRecommendation(**item) for item in DEFAULT_RECOMMENDATIONS]


def _detect_ethiopian_holiday(target: date, rules: list[dict]) -> str | None:
    _eth_year, eth_month, eth_day = _gregorian_to_ethiopian(
        target.year, target.month, target.day
    )

    for rule in rules:
        if rule["eth_month"] == eth_month and rule["eth_day"] == eth_day:
            return rule["key"]
    return None


@router.get("/playlists", response_model=schemas.PlaylistRecommendationResponse)
def recommend_playlists(
    date_str: str | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    target = date.today()
    if date_str:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()

    rules = _runtime_rules(db)
    holiday = _detect_ethiopian_holiday(target, rules)
    recommendations = _build_recommendations(holiday, rules)
    return {
        "date": target.isoformat(),
        "holiday": holiday,
        "recommendations": recommendations,
    }


@router.get("/hybrid-feed", response_model=schemas.HybridRecommendationResponse)
def hybrid_feed(
    date_str: str | None = Query(default=None, alias="date"),
    location: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    target = date.today()
    if date_str:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()

    rules = _runtime_rules(db)
    candidates = [SongCandidate(**song) for song in SONG_CATALOG]
    recommender = HybridRecommender(rules)
    ranked, holiday_key, backend = recommender.rank(
        songs=candidates,
        target_date=target,
        location=location,
        limit=limit,
    )

    return {
        "date": target.isoformat(),
        "holiday": holiday_key,
        "location": location,
        "model_backend": backend,
        "recommendations": ranked,
    }


@router.get("/for-you", response_model=schemas.PersonalizedFeedResponse)
def for_you(
    user_id: int,
    location: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    try:
        return crud.get_personalized_feed(
            db,
            user_id=user_id,
            location=location,
            limit=limit,
        )
    except ValueError as exc:
        if str(exc) == "user_not_found":
            raise HTTPException(status_code=404, detail="User not found") from exc
        raise


@router.get("/trending", response_model=schemas.TrendingFeedResponse)
def trending(
    location: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return crud.get_trending_feed(db, location=location, limit=limit)


@router.get("", response_model=schemas.PersonalizedFeedResponse)
def recommendations_root(
    user_id: int,
    location: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return for_you(user_id=user_id, location=location, limit=limit, db=db)
