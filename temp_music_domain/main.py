"""
Music domain main module.

This module initializes the music domain with all its components
and provides the main FastAPI application for music service.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from temp_music_domain.api import music_api
from temp_music_domain.config import get_music_config, initialize_music_services
from shared.db import get_db, create_tables
from shared.logging import configure_logging, get_logger
from shared.middleware import create_middleware_stack

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Music application starting up")
    
    # Initialize database tables
    try:
        create_tables()
        logger.info("Music domain database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create music domain database tables: {e}")
        raise
    
    # Initialize music services
    try:
        services = initialize_music_services()
        logger.info(f"Music domain services initialized: {list(services.keys())}")
        
        # Store services in app state for dependency injection
        app.state.music_services = services
        app.state.music_config = get_music_config()
        
    except Exception as e:
        logger.error(f"Failed to initialize music domain services: {e}")
        raise
    
    logger.info("Music application startup complete")
    yield
    logger.info("Music application shutting down")


# Create FastAPI application
app = FastAPI(
    title="Music Service",
    description="Music domain service for songs, playlists, and social features",
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.redoc_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan,
)

# Add middleware stack
create_middleware_stack(app, include_rate_limiting=True)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", 
        "Content-Type", 
        "X-Admin-Key", 
        "X-Request-ID",
        "X-Idempotency-Key",
    ],
)

# Include music API router
app.include_router(music_api)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "music"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check with service validation."""
    try:
        # Check database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        
        # Check music configuration
        music_config = app.state.music_config
        validation_results = music_config.validate_configuration()
        
        failed_validations = [
            check for check, passed in validation_results.items() 
            if not passed
        ]
        
        if failed_validations:
            return {
                "status": "degraded",
                "service": "music",
                "database": "healthy",
                "configuration": validation_results,
                "failed_validations": failed_validations
            }
        
        return {
            "status": "ready",
            "service": "music",
            "database": "healthy",
            "configuration": validation_results,
            "feature_flags": music_config.get_feature_flags()
        }
        
    except Exception as e:
        logger.error(f"Music readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "music",
                "error": str(e)
            }
        )


@app.get("/health/live")
async def liveness_check():
    """Liveness check."""
    return {"status": "alive", "service": "music"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    music_config = app.state.music_config
    
    return {
        "service": "Music Service",
        "version": "1.0.0",
        "description": "Music domain service for songs, playlists, and social features",
        "docs_url": "/docs" if settings.docs_enabled else None,
        "health_check": "/health",
        "feature_flags": music_config.get_feature_flags(),
        "environment": settings.app_env,
    }


# Configuration endpoint
@app.get("/config")
async def get_configuration():
    """Get music domain configuration."""
    music_config = app.state.music_config
    
    return {
        "storage": {
            "path": music_config.music_storage_path,
            "max_file_size_mb": music_config.max_file_size_mb,
            "allowed_formats": music_config.allowed_audio_formats,
        },
        "features": {
            "search_enabled": music_config.search_enabled,
            "marketplace_enabled": music_config.marketplace_enabled,
            "subscriptions_enabled": music_config.subscriptions_enabled,
            "social_features_enabled": music_config.social_features_enabled,
            "analytics_enabled": music_config.analytics_enabled,
        },
        "limits": {
            "max_playlist_songs": music_config.max_playlist_songs,
            "max_listing_price": music_config.max_listing_price,
            "premium_features": music_config.get_premium_features_list(),
        }
    }


# Storage information endpoint
@app.get("/storage")
async def get_storage_info():
    """Get storage information."""
    music_config = app.state.music_config
    return music_config.get_storage_info()


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(
        "Unhandled exception in music service",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "service": "music",
            "request_id": getattr(request.state, "request_id", None),
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Value error handler."""
    logger.warning(
        "Value error in music service",
        error=str(exc),
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_request",
            "message": str(exc),
            "service": "music",
            "request_id": getattr(request.state, "request_id", None),
        }
    )


# Development utilities
if __name__ == "__main__":
    import uvicorn
    
    # Run application
    uvicorn.run(
        "temp_music_domain.main:app",
        host="0.0.0.0",
        port=8002,  # Different port to avoid conflicts
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )


# Export main components
__all__ = [
    "app",
    "music_api",
]
