from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/playlists", response_model=schemas.PlaylistRecommendationResponse)
def playlist_recommendations(
    date_str: str | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
    return RecommendationService(db).recommend_playlists(target_date=target_date)


@router.get("/feed", response_model=schemas.PersonalizedFeedResponse)
def personalized_feed(
    user_id: int,
    location: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    date_str: str | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
        return RecommendationService(db).get_personalized_feed(
            user_id=user_id,
            location=location,
            limit=limit,
            target_date=target_date,
        )
    except ValueError as exc:
        if str(exc) == "user_not_found":
            raise HTTPException(status_code=404, detail="User not found") from exc
        raise


@router.get("/hybrid", response_model=schemas.HybridRecommendationResponse)
def hybrid_feed(
    user_id: int | None = None,
    location: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    date_str: str | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
    return RecommendationService(db).get_hybrid_feed(
        user_id=user_id,
        location=location,
        limit=limit,
        target_date=target_date,
    )


@router.get("/trending", response_model=schemas.TrendingFeedResponse)
def trending(
    location: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return RecommendationService(db).get_trending_feed(location=location, limit=limit)

