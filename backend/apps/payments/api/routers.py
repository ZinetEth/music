"""
Payment API routers - secure, reusable payment endpoints.

These routers provide a complete payment API that can be used
across multiple applications without coupling to specific business domains.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session

from apps.payments.services.payment_service import (
    PaymentService,
    PaymentServiceError,
    PaymentNotFoundError,
    InvalidPaymentStatusError,
    IdempotencyError,
)
from apps.payments.services.webhook_service import (
    WebhookService,
    WebhookServiceError,
    DuplicateWebhookError,
    WebhookVerificationFailedError,
    WebhookProcessingError,
)
from apps.payments.schemas import (
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentProcessRequest,
    PaymentProcessResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    RefundCreate,
    RefundResponse,
    WebhookEventResponse,
    PaymentIntentList,
    TransactionList,
    PaymentError,
    APIErrorResponse,
    ValidationError,
)
from apps.payments.models import PaymentStatus
from shared.db import get_db
from shared.auth import get_current_user_id, require_admin_key
from shared.logging import get_logger
from shared.middleware import get_request_id

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


# Dependency injection
def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    """Get payment service instance."""
    return PaymentService(db)


def get_webhook_service(db: Session = Depends(get_db)) -> WebhookService:
    """Get webhook service instance."""
    return WebhookService(db)


# Payment Intent endpoints
@router.post("/intents", response_model=PaymentIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_intent(
    request: PaymentIntentCreate,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    x_idempotency_key: Optional[str] = Header(None, description="Idempotency key for duplicate prevention"),
    request_id: str = Depends(get_request_id),
):
    """
    Create a new payment intent.
    
    This endpoint creates a payment intent that can be used across any application.
    The payment intent is generic and not tied to specific business objects.
    
    Args:
        request: Payment intent creation request
        x_idempotency_key: Optional idempotency key
        request_id: Request ID for tracing
    
    Returns:
        Created payment intent
    
    Raises:
        HTTPException: If creation fails
    """
    try:
        logger.info(
            "Creating payment intent",
            app_name=request.app_name,
            object_type=request.object_type,
            object_id=request.object_id,
            amount=request.amount,
            customer_id=request.customer_id,
            request_id=request_id,
        )
        
        payment_intent = await payment_service.create_payment_intent(
            request, idempotency_key=x_idempotency_key
        )
        
        logger.info(
            "Payment intent created successfully",
            payment_intent_id=payment_intent.id,
            request_id=request_id,
        )
        
        return payment_intent
        
    except IdempotencyError as e:
        logger.warning(
            "Idempotency key already used",
            idempotency_key=x_idempotency_key,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "idempotency_error",
                "message": "Idempotency key already used",
                "idempotency_key": x_idempotency_key,
                "request_id": request_id,
            }
        )
    
    except PaymentServiceError as e:
        logger.error(
            "Payment intent creation failed",
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "payment_creation_error",
                "message": str(e),
                "request_id": request_id,
            }
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error creating payment intent",
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


@router.get("/intents/{payment_intent_id}", response_model=PaymentIntentResponse)
async def get_payment_intent(
    payment_intent_id: int,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    request_id: str = Depends(get_request_id),
):
    """
    Get payment intent by ID.
    
    Args:
        payment_intent_id: Payment intent ID
        request_id: Request ID for tracing
    
    Returns:
        Payment intent details
    
    Raises:
        HTTPException: If payment intent not found
    """
    try:
        payment_intent = payment_service.get_payment_intent(payment_intent_id)
        
        logger.info(
            "Payment intent retrieved",
            payment_intent_id=payment_intent_id,
            request_id=request_id,
        )
        
        return payment_intent
        
    except PaymentNotFoundError as e:
        logger.warning(
            "Payment intent not found",
            payment_intent_id=payment_intent_id,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "payment_not_found",
                "message": str(e),
                "payment_intent_id": payment_intent_id,
                "request_id": request_id,
            }
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error getting payment intent",
            payment_intent_id=payment_intent_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


@router.get("/intents", response_model=PaymentIntentList)
async def list_payment_intents(
    app_name: Optional[str] = Query(None, description="Filter by app name"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    request_id: str = Depends(get_request_id),
):
    """
    List payment intents with optional filtering.
    
    Args:
        app_name: Filter by app name
        customer_id: Filter by customer ID
        status: Filter by status
        limit: Maximum number of results
        offset: Offset for pagination
        request_id: Request ID for tracing
    
    Returns:
        List of payment intents
    """
    try:
        payment_intents = payment_service.list_payment_intents(
            app_name=app_name,
            customer_id=customer_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        
        logger.info(
            "Payment intents listed",
            count=len(payment_intents),
            app_name=app_name,
            customer_id=customer_id,
            status=status,
            request_id=request_id,
        )
        
        return PaymentIntentList(
            items=payment_intents,
            total=len(payment_intents),
            page=offset // limit + 1,
            page_size=limit,
            has_next=len(payment_intents) == limit,
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error listing payment intents",
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


# Payment Processing endpoints
@router.post("/process", response_model=PaymentProcessResponse)
async def process_payment(
    request: PaymentProcessRequest,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    x_idempotency_key: Optional[str] = Header(None, description="Idempotency key for duplicate prevention"),
    request_id: str = Depends(get_request_id),
):
    """
    Process a payment through the specified provider.
    
    Args:
        request: Payment processing request
        x_idempotency_key: Optional idempotency key
        request_id: Request ID for tracing
    
    Returns:
        Payment processing response
    
    Raises:
        HTTPException: If processing fails
    """
    try:
        logger.info(
            "Processing payment",
            payment_intent_id=request.payment_intent_id,
            provider=request.provider,
            request_id=request_id,
        )
        
        process_response = await payment_service.process_payment(
            request, idempotency_key=x_idempotency_key
        )
        
        logger.info(
            "Payment processed successfully",
            payment_intent_id=request.payment_intent_id,
            provider=request.provider,
            next_action=process_response.next_action,
            request_id=request_id,
        )
        
        return process_response
        
    except PaymentNotFoundError as e:
        logger.warning(
            "Payment intent not found for processing",
            payment_intent_id=request.payment_intent_id,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "payment_not_found",
                "message": str(e),
                "payment_intent_id": request.payment_intent_id,
                "request_id": request_id,
            }
        )
    
    except InvalidPaymentStatusError as e:
        logger.warning(
            "Invalid payment status for processing",
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_payment_status",
                "message": str(e),
                "payment_intent_id": request.payment_intent_id,
                "request_id": request_id,
            }
        )
    
    except IdempotencyError as e:
        logger.warning(
            "Idempotency key already used for payment processing",
            idempotency_key=x_idempotency_key,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "idempotency_error",
                "message": "Idempotency key already used",
                "idempotency_key": x_idempotency_key,
                "request_id": request_id,
            }
        )
    
    except PaymentServiceError as e:
        logger.error(
            "Payment processing failed",
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "payment_processing_error",
                "message": str(e),
                "payment_intent_id": request.payment_intent_id,
                "request_id": request_id,
            }
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error processing payment",
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(
    request: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    request_id: str = Depends(get_request_id),
):
    """
    Verify payment status with the provider.
    
    Args:
        request: Payment verification request
        request_id: Request ID for tracing
    
    Returns:
        Payment verification response
    
    Raises:
        HTTPException: If verification fails
    """
    try:
        logger.info(
            "Verifying payment",
            payment_intent_id=request.payment_intent_id,
            provider=request.provider,
            request_id=request_id,
        )
        
        verify_response = await payment_service.verify_payment(request)
        
        logger.info(
            "Payment verification completed",
            payment_intent_id=request.payment_intent_id,
            is_verified=verify_response.is_verified,
            request_id=request_id,
        )
        
        return verify_response
        
    except PaymentNotFoundError as e:
        logger.warning(
            "Payment intent not found for verification",
            payment_intent_id=request.payment_intent_id,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "payment_not_found",
                "message": str(e),
                "payment_intent_id": request.payment_intent_id,
                "request_id": request_id,
            }
        )
    
    except PaymentServiceError as e:
        logger.error(
            "Payment verification failed",
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "payment_verification_error",
                "message": str(e),
                "payment_intent_id": request.payment_intent_id,
                "request_id": request_id,
            }
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error verifying payment",
            payment_intent_id=request.payment_intent_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


# Refund endpoints
@router.post("/refunds", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    request: RefundCreate,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    user_id: int = Depends(get_current_user_id),
    request_id: str = Depends(get_request_id),
):
    """
    Create a refund for a payment transaction.
    
    Args:
        request: Refund creation request
        user_id: Current user ID
        request_id: Request ID for tracing
    
    Returns:
        Created refund
    
    Raises:
        HTTPException: If refund creation fails
    """
    try:
        logger.info(
            "Creating refund",
            original_transaction_id=request.original_transaction_id,
            amount=request.amount,
            user_id=user_id,
            request_id=request_id,
        )
        
        # Set refunded_by to current user if not provided
        if not request.refunded_by:
            request.refunded_by = str(user_id)
        
        refund = await payment_service.create_refund(request)
        
        logger.info(
            "Refund created successfully",
            refund_id=refund.id,
            original_transaction_id=request.original_transaction_id,
            request_id=request_id,
        )
        
        return RefundResponse(
            id=refund.id,
            original_transaction_id=refund.original_transaction_id,
            amount=refund.amount,
            currency=refund.currency,
            reason=refund.reason,
            status=refund.status,
            provider_refund_id=refund.provider_refund_id,
            provider_response=refund.provider_response,
            failure_reason=refund.failure_reason,
            metadata=refund.metadata,
            refunded_by=refund.refunded_by,
            created_at=refund.created_at,
            updated_at=refund.updated_at,
            processed_at=refund.processed_at,
        )
        
    except PaymentNotFoundError as e:
        logger.warning(
            "Original transaction not found for refund",
            original_transaction_id=request.original_transaction_id,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "transaction_not_found",
                "message": str(e),
                "original_transaction_id": request.original_transaction_id,
                "request_id": request_id,
            }
        )
    
    except InvalidPaymentStatusError as e:
        logger.warning(
            "Invalid transaction status for refund",
            original_transaction_id=request.original_transaction_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_transaction_status",
                "message": str(e),
                "original_transaction_id": request.original_transaction_id,
                "request_id": request_id,
            }
        )
    
    except PaymentServiceError as e:
        logger.error(
            "Refund creation failed",
            original_transaction_id=request.original_transaction_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "refund_creation_error",
                "message": str(e),
                "original_transaction_id": request.original_transaction_id,
                "request_id": request_id,
            }
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error creating refund",
            original_transaction_id=request.original_transaction_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


# Webhook endpoints
@router.post("/webhooks/{provider_name}", status_code=status.HTTP_200_OK)
async def process_webhook(
    provider_name: str,
    payload: Dict[str, Any],
    headers: Dict[str, str] = Header(None),
    db: Session = Depends(get_db),
    webhook_service: WebhookService = Depends(get_webhook_service),
    request_id: str = Depends(get_request_id),
):
    """
    Process webhook from payment provider.
    
    Args:
        provider_name: Name of the payment provider
        payload: Webhook payload
        headers: HTTP headers
        request_id: Request ID for tracing
    
    Returns:
        Webhook processing response
    
    Raises:
        HTTPException: If webhook processing fails
    """
    try:
        logger.info(
            "Processing webhook",
            provider=provider_name,
            request_id=request_id,
        )
        
        # Convert payload to JSON string
        import json
        payload_str = json.dumps(payload)
        
        webhook_response = await webhook_service.process_webhook(
            provider_name, payload_str, headers
        )
        
        logger.info(
            "Webhook processed successfully",
            provider=provider_name,
            webhook_id=webhook_response.id,
            event_type=webhook_response.event_type,
            request_id=request_id,
        )
        
        return {"status": "processed", "webhook_id": webhook_response.id}
        
    except DuplicateWebhookError as e:
        logger.warning(
            "Duplicate webhook received",
            provider=provider_name,
            error=str(e),
            request_id=request_id,
        )
        return {"status": "duplicate", "message": str(e)}
    
    except WebhookVerificationFailedError as e:
        logger.warning(
            "Webhook verification failed",
            provider=provider_name,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "webhook_verification_failed",
                "message": str(e),
                "provider": provider_name,
                "request_id": request_id,
            }
        )
    
    except WebhookProcessingError as e:
        logger.error(
            "Webhook processing failed",
            provider=provider_name,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "webhook_processing_error",
                "message": str(e),
                "provider": provider_name,
                "request_id": request_id,
            }
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error processing webhook",
            provider=provider_name,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


# Admin endpoints
@router.get("/admin/webhooks", response_model=List[WebhookEventResponse])
async def list_webhooks(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    webhook_service: WebhookService = Depends(get_webhook_service),
    admin_key: str = Depends(require_admin_key),
    request_id: str = Depends(get_request_id),
):
    """
    List webhook events (admin only).
    
    Args:
        provider: Filter by provider
        status: Filter by status
        limit: Maximum number of results
        offset: Offset for pagination
        admin_key: Admin API key
        request_id: Request ID for tracing
    
    Returns:
        List of webhook events
    """
    try:
        webhooks = webhook_service.list_webhooks(
            provider=provider,
            status=status,
            limit=limit,
            offset=offset,
        )
        
        logger.info(
            "Webhooks listed (admin)",
            count=len(webhooks),
            provider=provider,
            status=status,
            request_id=request_id,
        )
        
        return webhooks
        
    except Exception as e:
        logger.error(
            "Unexpected error listing webhooks",
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )


@router.post("/admin/webhooks/{webhook_event_id}/retry", response_model=WebhookEventResponse)
async def retry_webhook(
    webhook_event_id: int,
    db: Session = Depends(get_db),
    webhook_service: WebhookService = Depends(get_webhook_service),
    admin_key: str = Depends(require_admin_key),
    request_id: str = Depends(get_request_id),
):
    """
    Retry processing a failed webhook event (admin only).
    
    Args:
        webhook_event_id: Webhook event ID
        admin_key: Admin API key
        request_id: Request ID for tracing
    
    Returns:
        Processed webhook event
    
    Raises:
        HTTPException: If retry fails
    """
    try:
        logger.info(
            "Retrying webhook (admin)",
            webhook_event_id=webhook_event_id,
            request_id=request_id,
        )
        
        webhook_response = await webhook_service.retry_failed_webhook(webhook_event_id)
        
        logger.info(
            "Webhook retry completed",
            webhook_event_id=webhook_event_id,
            status=webhook_response.status,
            request_id=request_id,
        )
        
        return webhook_response
        
    except WebhookServiceError as e:
        logger.error(
            "Webhook retry failed",
            webhook_event_id=webhook_event_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "webhook_retry_failed",
                "message": str(e),
                "webhook_event_id": webhook_event_id,
                "request_id": request_id,
            }
        )
    
    except Exception as e:
        logger.error(
            "Unexpected error retrying webhook",
            webhook_event_id=webhook_event_id,
            error=str(e),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        )
