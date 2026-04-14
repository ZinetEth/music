from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.utils.helpers import utc_now


class ListeningSession(Base):
    __tablename__ = "listening_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active")
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    target_session_minutes = Column(Integer, nullable=False, default=45)

    user = relationship("User", back_populates="listening_sessions")
    recommendation_events = relationship(
        "SessionRecommendationEvent",
        back_populates="session",
    )


class SessionRecommendationEvent(Base):
    __tablename__ = "session_recommendation_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("listening_sessions.id"), nullable=False, index=True)
    song_id = Column(String(255), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    accepted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    session = relationship("ListeningSession", back_populates="recommendation_events")

