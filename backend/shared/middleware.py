"""
Shared middleware utilities.

This provides common middleware that can be used across
all domains in the multi-app architecture.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from shared.auth import check_rate_limit
from shared.logging import get_logger, request_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to all requests.
    
    This helps with tracing and debugging requests across the system.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


def get_request_id(request: Request) -> str:
    """
    Get request ID from request state.
    
    Args:
        request: FastAPI request
        
    Returns:
        Request ID
    """
    return getattr(request.state, "request_id", "unknown")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.
    
    This provides comprehensive request logging for monitoring
    and debugging purposes.
    """
    
    def __init__(self, app, logger_name: str = "request"):
        super().__init__(app)
        self.request_logger = request_logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request ID
        request_id = get_request_id(request)
        
        # Get user ID if available
        user_id = getattr(request.state, "user_id", None)
        
        # Log request start
        self.request_logger.log_request(
            method=request.method,
            path=request.url.path,
            query_string=str(request.url.query) if request.url.query else None,
            user_id=user_id,
            request_id=request_id,
            user_agent=request.headers.get("user-agent"),
            ip_address=self._get_client_ip(request),
        )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        self.request_logger.log_response(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            request_id=request_id,
            response_size=response.headers.get("content-length"),
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client IP
        return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to requests.
    
    This provides basic rate limiting to prevent abuse.
    """
    
    def __init__(self, app, requests_per_minute: int = 60, key_func: Callable = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.key_func = key_func or self._default_key_func
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get rate limit key
        key = self.key_func(request)
        
        # Check rate limit
        if not check_rate_limit(key, self.requests_per_minute, 60):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests",
                    "limit": self.requests_per_minute,
                    "window": 60
                },
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)
    
    def _default_key_func(self, request: Request) -> str:
        """Default rate limit key based on IP address."""
        ip_address = request.headers.get("x-forwarded-for")
        if ip_address:
            return f"ip:{ip_address.split(',')[0].strip()}"
        
        ip_address = request.headers.get("x-real-ip")
        if ip_address:
            return f"ip:{ip_address}"
        
        return f"ip:{request.client.host}" if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    
    This adds various security headers to improve security.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Add CSP header
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle errors consistently.
    
    This provides consistent error responses and logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # Get request ID for logging
            request_id = get_request_id(request)
            
            # Log error
            logger.error(
                "unhandled_exception",
                error=str(e),
                error_type=type(e).__name__,
                path=request.url.path,
                method=request.method,
                request_id=request_id,
                exc_info=True
            )
            
            # Return consistent error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "Internal server error",
                    "request_id": request_id
                }
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect basic metrics.
    
    This provides basic request metrics for monitoring.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            self.request_count += 1
            return response
        except Exception as e:
            self.error_count += 1
            raise
        finally:
            response_time = time.time() - start_time
            self.total_response_time += response_time
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_response_time = (
            self.total_response_time / self.request_count
            if self.request_count > 0 else 0
        )
        
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "average_response_time": avg_response_time,
            "total_response_time": self.total_response_time
        }


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add user context to requests.
    
    This extracts user information from authentication tokens
    and adds it to request state for easy access.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Try to get user ID from token
        try:
            from shared.auth import get_optional_user_id
            user_id = get_optional_user_id(request)
            if user_id:
                request.state.user_id = user_id
        except Exception:
            # If authentication fails, continue without user context
            pass
        
        return await call_next(request)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate common request parameters.
    
    This provides basic validation for common parameters.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            return JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "message": "Request payload too large"
                }
            )
        
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith(("application/json", "multipart/form-data")):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "invalid_content_type",
                        "message": "Invalid content type"
                    }
                )
        
        return await call_next(request)


# Middleware factory functions
def create_middleware_stack(app, include_rate_limiting: bool = True) -> None:
    """
    Create the standard middleware stack.
    
    Args:
        app: FastAPI application
        include_rate_limiting: Whether to include rate limiting middleware
    """
    # Add request ID middleware (first)
    app.add_middleware(RequestIDMiddleware)
    
    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add user context
    app.add_middleware(UserContextMiddleware)
    
    # Add validation
    app.add_middleware(ValidationMiddleware)
    
    # Add rate limiting (optional)
    if include_rate_limiting:
        app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
    
    # Add request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add metrics
    app.add_middleware(MetricsMiddleware)
    
    # Add error handling (last)
    app.add_middleware(ErrorHandlingMiddleware)
