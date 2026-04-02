"""
Shared database configuration and base model.

This provides a common database setup that can be used across
all domains in the multi-app architecture.
"""

from datetime import UTC, datetime
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.settings import get_settings

# Create base model for all domain models
Base = declarative_base()

# Database configuration
settings = get_settings()

# Create engine based on database type
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.database_echo,
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=settings.db_pool_timeout,
        echo=settings.database_echo,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency to get database session.
    
    This is the standard FastAPI dependency that provides a database
    session for each request. The session is automatically closed
    when the request is completed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator:
    """
    Async dependency to get database session.
    
    For use with async endpoints and services.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)


# Database utility functions
def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)


def get_database_info() -> dict:
    """Get database connection information."""
    return {
        "database_url": settings.database_url.split("@")[1] if "@" in settings.database_url else "sqlite",
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "echo": settings.database_echo,
        "is_sqlite": settings.database_url.startswith("sqlite"),
        "is_postgres": settings.database_url.startswith("postgresql"),
    }
