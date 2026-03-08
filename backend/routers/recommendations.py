from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import crud
import schemas
from config.holidays import DEFAULT_RECOMMENDATIONS, HOLIDAY_RULES
from config.recommendation_catalog import SONG_CATALOG
from database import get_db
from recommender_engine import HybridRecommender, SongCandidate
from routers.calendar import _gregorian_to_ethiopian

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
                return [schemas.PlaylistRecommendation(**item) for item in rule["recommendations"]]

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
