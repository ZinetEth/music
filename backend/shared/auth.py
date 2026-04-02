"""
Shared authentication and authorization utilities.

This provides secure authentication that can be used across
all domains in the multi-app architecture.
"""

import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.settings import get_settings
from shared.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer scheme for token authentication
bearer_scheme = HTTPBearer(auto_error=False)

# Settings
settings = get_settings()


def create_api_key() -> str:
    """
    Create a secure API key.
    
    Returns:
        Secure random API key
    """
    return secrets.token_urlsafe(32)


def verify_api_key(api_key: str, expected_key: str) -> bool:
    """
    Verify API key using constant-time comparison.
    
    Args:
        api_key: Provided API key
        expected_key: Expected API key
        
    Returns:
        True if API key is valid
    """
    return secrets.compare_digest(api_key, expected_key)


def require_admin_key(
    x_admin_key: Optional[str] = Header(None, description="Admin API key")
) -> str:
    """
    Require admin API key for admin endpoints.
    
    Args:
        x_admin_key: Admin API key from header
        
    Returns:
        Valid admin key
        
    Raises:
        HTTPException: If admin key is invalid
    """
    if not x_admin_key or not verify_api_key(x_admin_key, settings.admin_api_key):
        logger.warning(
            "Invalid admin key provided",
            admin_key=x_admin_key[:8] + "..." if x_admin_key else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return x_admin_key


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> int:
    """
    Get current user ID from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID
        
    Raises:
        HTTPException: If token is invalid
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        from app.core.auth import decode_access_token
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        return user_id
    except Exception as e:
        logger.warning(
            "Invalid token provided",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[int]:
    """
    Get optional user ID from JWT token.
    
    This function doesn't raise an exception if authentication fails,
    making it suitable for endpoints that can work without authentication.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID or None if not authenticated
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    
    try:
        from app.core.auth import decode_access_token
        payload = decode_access_token(credentials.credentials)
        return int(payload["sub"])
    except Exception:
        return None


def check_user_permission(
    user_id: int,
    required_permission: str,
    resource_id: Optional[str] = None
) -> bool:
    """
    Check if user has permission for a specific action.
    
    Args:
        user_id: User ID
        required_permission: Required permission
        resource_id: Optional resource ID
        
    Returns:
        True if user has permission
    """
    # This is a placeholder implementation
    # In a real application, you would check against a permission system
    
    # For now, allow all authenticated users
    return True


def require_permission(permission: str):
    """
    Decorator to require specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
    """
    def permission_dependency(
        user_id: int = Depends(get_current_user_id),
        resource_id: Optional[str] = None
    ) -> int:
        if not check_user_permission(user_id, permission, resource_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        return user_id
    
    return permission_dependency


class RoleChecker:
    """
    Role-based access control utility.
    """
    
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, user_id: int = Depends(get_current_user_id)) -> int:
        """
        Check if user has allowed role.
        
        Args:
            user_id: User ID
            
        Returns:
            User ID if authorized
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        # This is a placeholder implementation
        # In a real application, you would check against user roles
        
        # For now, allow all users
        return user_id


# Common role checkers
require_admin = RoleChecker(["admin"])
require_moderator = RoleChecker(["admin", "moderator"])
require_user = RoleChecker(["admin", "moderator", "user"])


def create_access_token_with_permissions(
    user_id: int,
    permissions: list[str],
    expires_in_seconds: Optional[int] = None
) -> str:
    """
    Create JWT token with permission claims.
    
    Args:
        user_id: User ID
        permissions: List of permissions
        expires_in_seconds: Token expiration time
        
    Returns:
        JWT token
    """
    from app.core.auth import create_access_token
    
    # Add permissions to token payload
    # This would require modifying the JWT creation to include custom claims
    return create_access_token(user_id, expires_in_seconds)


def extract_permissions_from_token(token: str) -> list[str]:
    """
    Extract permissions from JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        List of permissions
    """
    from app.core.auth import decode_access_token
    
    try:
        payload = decode_access_token(token)
        return payload.get("permissions", [])
    except Exception:
        return []


# Security utilities
def generate_secure_random(length: int = 32) -> str:
    """
    Generate secure random string.
    
    Args:
        length: Length of random string
        
    Returns:
        Secure random string
    """
    return secrets.token_urlsafe(length)


def hash_sensitive_data(data: str, salt: Optional[str] = None) -> str:
    """
    Hash sensitive data for storage.
    
    Args:
        data: Data to hash
        salt: Optional salt
        
    Returns:
        Hashed data
    """
    import hashlib
    
    if salt is None:
        salt = settings.secret_key
    
    return hashlib.sha256((data + salt).encode()).hexdigest()


def verify_sensitive_data(data: str, hashed_data: str, salt: Optional[str] = None) -> bool:
    """
    Verify sensitive data against hash.
    
    Args:
        data: Original data
        hashed_data: Hashed data
        salt: Optional salt
        
    Returns:
        True if data matches hash
    """
    return hash_sensitive_data(data, salt) == hashed_data


# Rate limiting utilities
class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    In production, use Redis or another distributed cache.
    """
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> bool:
        """
        Check if request is allowed.
        
        Args:
            key: Rate limit key (e.g., user ID, IP)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed
        """
        import time
        
        now = time.time()
        window_start = now - window_seconds
        
        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
        else:
            self.requests[key] = []
        
        # Check limit
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int = 60
) -> bool:
    """
    Check rate limit for given key.
    
    Args:
        key: Rate limit key
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
        
    Returns:
        True if request is allowed
    """
    return rate_limiter.is_allowed(key, limit, window_seconds)
