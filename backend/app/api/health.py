"""
Health check endpoints for the music platform backend.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import time

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    Returns the status of the backend service.
    """
    try:
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "music-platform-backend",
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check with component status.
    """
    try:
        # Check database connection (simplified)
        db_status = "healthy"  # In a real implementation, check actual DB connection
        
        # Check payment providers (simplified)
        payment_status = "healthy"  # In a real implementation, check provider availability
        
        overall_status = "healthy" if db_status == "healthy" and payment_status == "healthy" else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "service": "music-platform-backend",
            "version": "1.0.0",
            "components": {
                "database": db_status,
                "payments": payment_status,
                "api": "healthy"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "service": "music-platform-backend",
                "error": str(e)
            }
        )


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for connectivity testing.
    """
    return {"pong": time.time()}
