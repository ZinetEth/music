"""
Authentication endpoints for music platform compatibility.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str = "music_platform_user"
    password: str = "default_password"

class LoginResponse(BaseModel):
    success: bool = True
    message: str = "Music Platform Authentication"
    userId: str = "1"
    token: str = "music_platform_token"
    expires_in: int = 3600

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Compatibility endpoint for Feishin authentication.
    This accepts Navidrome-style login requests but authenticates for our music platform.
    """
    try:
        # For our music platform, we accept any login and return a success response
        # In a real implementation, you might validate against actual user credentials
        
        return LoginResponse(
            success=True,
            message="Music Platform Authentication Successful",
            userId="1",
            token=f"music_platform_token_{int(time.time())}",
            expires_in=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.get("/status")
async def auth_status():
    """
    Check authentication status.
    """
    return {
        "authenticated": True,
        "platform": "music_platform",
        "message": "Music Platform authentication is active"
    }
