import logging
import structlog
import sys
from typing import Any, Dict


def configure_logging(level: str) -> None:
    """Configure structured logging with structlog."""
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggingMiddleware:
    """Middleware to add request context to logs."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            import time
            start_time = time.time()
            
            # Add request context to logger
            logger = get_logger("request")
            request_id = scope.get("headers", {}).get(b"x-request-id", b"").decode()
            
            logger.info(
                "request_started",
                method=scope["method"],
                path=scope["path"],
                request_id=request_id
            )
            
            # Process request
            try:
                await self.app(scope, receive, send)
                duration = time.time() - start_time
                logger.info(
                    "request_completed",
                    method=scope["method"],
                    path=scope["path"],
                    request_id=request_id,
                    duration=duration
                )
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "request_failed",
                    method=scope["method"],
                    path=scope["path"],
                    request_id=request_id,
                    duration=duration,
                    error=str(e)
                )
                raise
        else:
            await self.app(scope, receive, send)
