"""
Shared logging utilities.

This provides structured logging that can be used across
all domains in the multi-app architecture.
"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger

from app.core.settings import get_settings


def configure_logging() -> None:
    """
    Configure structured logging for the application.
    
    This sets up both standard logging and structlog for
    consistent, structured log output.
    """
    settings = get_settings()
    
    # Configure standard logging
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(
        jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root_logger.addHandler(log_handler)
    
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
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class RequestLogger:
    """
    Request logging utility for API requests.
    """
    
    def __init__(self, logger_name: str = "request"):
        self.logger = get_logger(logger_name)
    
    def log_request(
        self,
        method: str,
        path: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log incoming request.
        
        Args:
            method: HTTP method
            path: Request path
            user_id: User ID if authenticated
            request_id: Request ID for tracing
            **kwargs: Additional request data
        """
        self.logger.info(
            "request_started",
            method=method,
            path=path,
            user_id=user_id,
            request_id=request_id,
            **kwargs
        )
    
    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log request response.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            user_id: User ID if authenticated
            request_id: Request ID for tracing
            **kwargs: Additional response data
        """
        log_level = "error" if status_code >= 500 else "warning" if status_code >= 400 else "info"
        
        getattr(self.logger, log_level)(
            "request_completed",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            request_id=request_id,
            **kwargs
        )


class PaymentLogger:
    """
    Payment logging utility for payment operations.
    """
    
    def __init__(self, logger_name: str = "payment"):
        self.logger = get_logger(logger_name)
    
    def log_payment_created(
        self,
        payment_intent_id: int,
        amount: float,
        currency: str,
        customer_id: str,
        provider: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log payment creation.
        
        Args:
            payment_intent_id: Payment intent ID
            amount: Payment amount
            currency: Payment currency
            customer_id: Customer ID
            provider: Payment provider
            request_id: Request ID for tracing
            **kwargs: Additional payment data
        """
        self.logger.info(
            "payment_created",
            payment_intent_id=payment_intent_id,
            amount=amount,
            currency=currency,
            customer_id=customer_id,
            provider=provider,
            request_id=request_id,
            **kwargs
        )
    
    def log_payment_processed(
        self,
        payment_intent_id: int,
        provider: str,
        status: str,
        transaction_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log payment processing.
        
        Args:
            payment_intent_id: Payment intent ID
            provider: Payment provider
            status: Payment status
            transaction_id: Transaction ID
            request_id: Request ID for tracing
            **kwargs: Additional processing data
        """
        log_level = "error" if status == "failed" else "info"
        
        getattr(self.logger, log_level)(
            "payment_processed",
            payment_intent_id=payment_intent_id,
            provider=provider,
            status=status,
            transaction_id=transaction_id,
            request_id=request_id,
            **kwargs
        )
    
    def log_payment_verified(
        self,
        payment_intent_id: int,
        provider: str,
        is_verified: bool,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log payment verification.
        
        Args:
            payment_intent_id: Payment intent ID
            provider: Payment provider
            is_verified: Whether payment was verified
            request_id: Request ID for tracing
            **kwargs: Additional verification data
        """
        log_level = "info" if is_verified else "warning"
        
        getattr(self.logger, log_level)(
            "payment_verified",
            payment_intent_id=payment_intent_id,
            provider=provider,
            is_verified=is_verified,
            request_id=request_id,
            **kwargs
        )
    
    def log_refund_created(
        self,
        refund_id: int,
        original_transaction_id: int,
        amount: float,
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log refund creation.
        
        Args:
            refund_id: Refund ID
            original_transaction_id: Original transaction ID
            amount: Refund amount
            reason: Refund reason
            request_id: Request ID for tracing
            **kwargs: Additional refund data
        """
        self.logger.info(
            "refund_created",
            refund_id=refund_id,
            original_transaction_id=original_transaction_id,
            amount=amount,
            reason=reason,
            request_id=request_id,
            **kwargs
        )
    
    def log_webhook_processed(
        self,
        provider: str,
        event_type: str,
        event_id: str,
        status: str,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log webhook processing.
        
        Args:
            provider: Payment provider
            event_type: Event type
            event_id: Event ID
            status: Processing status
            request_id: Request ID for tracing
            **kwargs: Additional webhook data
        """
        log_level = "error" if status == "failed" else "info"
        
        getattr(self.logger, log_level)(
            "webhook_processed",
            provider=provider,
            event_type=event_type,
            event_id=event_id,
            status=status,
            request_id=request_id,
            **kwargs
        )


class SecurityLogger:
    """
    Security logging utility for security events.
    """
    
    def __init__(self, logger_name: str = "security"):
        self.logger = get_logger(logger_name)
    
    def log_authentication_attempt(
        self,
        user_id: Optional[str],
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log authentication attempt.
        
        Args:
            user_id: User ID if available
            success: Whether authentication succeeded
            ip_address: Client IP address
            user_agent: User agent string
            request_id: Request ID for tracing
            **kwargs: Additional auth data
        """
        log_level = "info" if success else "warning"
        
        getattr(self.logger, log_level)(
            "authentication_attempt",
            user_id=user_id,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            **kwargs
        )
    
    def log_authorization_failure(
        self,
        user_id: Optional[str],
        required_permission: str,
        resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log authorization failure.
        
        Args:
            user_id: User ID if available
            required_permission: Required permission
            resource: Resource being accessed
            ip_address: Client IP address
            request_id: Request ID for tracing
            **kwargs: Additional authz data
        """
        self.logger.warning(
            "authorization_failure",
            user_id=user_id,
            required_permission=required_permission,
            resource=resource,
            ip_address=ip_address,
            request_id=request_id,
            **kwargs
        )
    
    def log_suspicious_activity(
        self,
        activity_type: str,
        user_id: Optional[str],
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log suspicious activity.
        
        Args:
            activity_type: Type of suspicious activity
            user_id: User ID if available
            ip_address: Client IP address
            details: Additional details about the activity
            request_id: Request ID for tracing
            **kwargs: Additional activity data
        """
        self.logger.error(
            "suspicious_activity",
            activity_type=activity_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {},
            request_id=request_id,
            **kwargs
        )


# Global logger instances
request_logger = RequestLogger()
payment_logger = PaymentLogger()
security_logger = SecurityLogger()


# Logging utilities
def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive data for logging.
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data
    """
    sensitive_fields = [
        "password", "token", "secret", "key", "api_key",
        "credit_card", "ssn", "social_security", "bank_account"
    ]
    
    sanitized = data.copy()
    
    for key, value in sanitized.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_for_logging(value)
        elif any(sensitive_field in key.lower() for sensitive_field in sensitive_fields):
            sanitized[key] = "[REDACTED]"
    
    return sanitized


def log_function_call(func_name: str, args: tuple, kwargs: dict, result: Any = None) -> None:
    """
    Log function call for debugging.
    
    Args:
        func_name: Function name
        args: Function arguments
        kwargs: Function keyword arguments
        result: Function result
    """
    logger = get_logger("function_call")
    
    log_data = {
        "function": func_name,
        "args_count": len(args),
        "kwargs_keys": list(kwargs.keys()),
    }
    
    if result is not None:
        log_data["result_type"] = type(result).__name__
    
    logger.debug("function_called", **log_data)


# Context manager for logging
class LogContext:
    """
    Context manager for adding context to log messages.
    """
    
    def __init__(self, logger: structlog.stdlib.BoundLogger, **context):
        self.logger = logger
        self.context = context
        self.bound_logger = None
    
    def __enter__(self):
        self.bound_logger = self.logger.bind(**self.context)
        return self.bound_logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.bound_logger.error(
                "context_exception",
                exception_type=exc_type.__name__,
                exception_message=str(exc_val),
                **self.context
            )
        return False


# Decorator for logging function calls
def log_calls(logger_name: str = "function"):
    """
    Decorator to log function calls.
    
    Args:
        logger_name: Logger name to use
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            
            try:
                result = func(*args, **kwargs)
                logger.info(
                    "function_success",
                    function=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys()),
                    result_type=type(result).__name__
                )
                return result
            except Exception as e:
                logger.error(
                    "function_error",
                    function=func.__name__,
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys()),
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise
        
        return wrapper
    return decorator
