import logging
import time
import uuid
from collections import defaultdict
from typing import Dict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"

        logger.info(
            "request_processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        return response


class MaxRequestSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large"},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Clean old requests (older than 1 minute)
        current_time = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                requests_count=len(self.requests[client_ip]),
                limit=self.requests_per_minute
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": self.requests_per_minute,
                    "window": "60 seconds"
                },
                headers={"Retry-After": "60"}
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)


class CacheMiddleware(BaseHTTPMiddleware):
    """Simple caching middleware for GET requests."""
    
    def __init__(self, app, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, tuple] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        cache_key = f"{request.url}:{request.headers.get('accept', '')}"
        current_time = time.time()
        
        # Check cache
        if cache_key in self.cache:
            cached_response, cached_time = self.cache[cache_key]
            if current_time - cached_time < self.cache_ttl:
                logger.debug(
                    "cache_hit",
                    cache_key=cache_key,
                    age=current_time - cached_time
                )
                return Response(
                    content=cached_response["body"],
                    status_code=cached_response["status_code"],
                    headers=cached_response["headers"],
                    media_type=cached_response["media_type"]
                )
        
        # Process request and cache response
        response = await call_next(request)
        
        # Only cache successful responses
        if response.status_code == 200:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            self.cache[cache_key] = (
                {
                    "body": response_body,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type
                },
                current_time
            )
            
            logger.debug(
                "cache_set",
                cache_key=cache_key,
                ttl=self.cache_ttl
            )
            
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type
            )
        
        return response
