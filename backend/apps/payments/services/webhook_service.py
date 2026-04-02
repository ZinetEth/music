"""
Webhook service - handles payment provider webhooks securely.

This service processes webhooks from payment providers with proper
verification, idempotency, and error handling.
"""

import hashlib
import hmac
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from apps.payments.models import (
    PaymentIntent,
    PaymentTransaction,
    WebhookEvent,
    WebhookStatus,
    PaymentStatus,
)
from apps.payments.providers.base import BasePaymentProvider, WebhookVerificationError
from apps.payments.schemas import WebhookEventCreate, WebhookEventResponse
from shared.db import Base


class WebhookServiceError(Exception):
    """Base exception for webhook service errors."""
    pass


class DuplicateWebhookError(WebhookServiceError):
    """Raised when webhook event is a duplicate."""
    pass


class WebhookVerificationFailedError(WebhookServiceError):
    """Raised when webhook verification fails."""
    pass


class WebhookProcessingError(WebhookServiceError):
    """Raised when webhook processing fails."""
    pass


class WebhookService:
    """
    Webhook processing service with security and idempotency controls.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._providers: Dict[str, BasePaymentProvider] = {}
    
    def register_provider(self, provider: BasePaymentProvider) -> None:
        """Register a payment provider for webhook processing."""
        self._providers[provider.get_provider_name()] = provider
    
    def get_provider(self, provider_name: str) -> BasePaymentProvider:
        """Get a registered payment provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            raise WebhookServiceError(f"Provider {provider_name} not registered")
        return provider
    
    async def process_webhook(
        self, 
        provider_name: str,
        payload: str,
        headers: Dict[str, str],
        signature: Optional[str] = None
    ) -> WebhookEventResponse:
        """
        Process a webhook from a payment provider.
        
        Args:
            provider_name: Name of the payment provider
            payload: Raw webhook payload
            headers: HTTP headers
            signature: Webhook signature (if not in headers)
            
        Returns:
            Processed webhook event response
            
        Raises:
            WebhookVerificationFailedError: If webhook verification fails
            DuplicateWebhookError: If webhook is a duplicate
            WebhookProcessingError: If processing fails
        """
        # Get provider
        provider = self.get_provider(provider_name)
        
        # Parse payload to extract event ID
        try:
            import json
            payload_data = json.loads(payload)
            event_id = payload_data.get('id') or payload_data.get('event_id') or payload_data.get('tx_ref')
            
            if not event_id:
                raise WebhookVerificationFailedError("Webhook payload missing event ID")
            
        except json.JSONDecodeError as e:
            raise WebhookVerificationFailedError(f"Invalid webhook JSON: {e}")
        
        # Check for duplicate webhook
        existing_webhook = self._find_duplicate_webhook(provider_name, event_id)
        if existing_webhook:
            raise DuplicateWebhookError(f"Webhook event {event_id} from {provider_name} already processed")
        
        # Verify webhook signature
        signature = signature or self._extract_signature_from_headers(headers)
        if not signature:
            raise WebhookVerificationFailedError("Missing webhook signature")
        
        if not provider.verify_webhook_signature(payload, signature, headers):
            raise WebhookVerificationFailedError("Invalid webhook signature")
        
        try:
            # Create webhook event record
            webhook_event = WebhookEvent(
                provider=provider_name,
                event_type=payload_data.get('type', 'unknown'),
                event_id=event_id,
                raw_payload=payload_data,
                status=WebhookStatus.PENDING.value,
                signature_verified=True,
                received_at=datetime.utcnow(),
            )
            
            self.db.add(webhook_event)
            self.db.commit()
            self.db.refresh(webhook_event)
            
            # Process webhook with provider
            processed_data = await provider.process_webhook(
                WebhookEventCreate(
                    provider=provider_name,
                    event_type=webhook_event.event_type,
                    event_id=event_id,
                    raw_payload=payload_data,
                )
            )
            
            # Update webhook with processed data
            webhook_event.processed_payload = processed_data
            webhook_event.status = WebhookStatus.PROCESSED.value
            webhook_event.processed_at = datetime.utcnow()
            webhook_event.processing_attempts = 1
            
            # Update payment status if applicable
            await self._update_payment_from_webhook(webhook_event, processed_data)
            
            self.db.commit()
            self.db.refresh(webhook_event)
            
            return self._map_to_webhook_response(webhook_event)
            
        except Exception as e:
            # Update webhook status to failed
            webhook_event.status = WebhookStatus.FAILED.value
            webhook_event.failure_reason = str(e)
            webhook_event.processing_attempts += 1
            webhook_event.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            raise WebhookProcessingError(f"Webhook processing failed: {e}")
    
    async def retry_failed_webhook(self, webhook_event_id: int) -> WebhookEventResponse:
        """
        Retry processing a failed webhook event.
        
        Args:
            webhook_event_id: ID of the webhook event to retry
            
        Returns:
            Processed webhook event response
            
        Raises:
            WebhookProcessingError: If retry fails
        """
        webhook_event = self.db.query(WebhookEvent).filter(
            WebhookEvent.id == webhook_event_id
        ).first()
        
        if not webhook_event:
            raise WebhookServiceError(f"Webhook event {webhook_event_id} not found")
        
        if webhook_event.status != WebhookStatus.FAILED.value:
            raise WebhookServiceError(f"Webhook event {webhook_event_id} is not in failed status")
        
        # Check retry limits
        if webhook_event.processing_attempts >= 5:
            raise WebhookServiceError(f"Webhook event {webhook_event_id} has exceeded retry limit")
        
        # Get provider
        provider = self.get_provider(webhook_event.provider)
        
        try:
            # Reset webhook status
            webhook_event.status = WebhookStatus.RETRYING.value
            webhook_event.processing_attempts += 1
            self.db.commit()
            
            # Process webhook again
            processed_data = await provider.process_webhook(
                WebhookEventCreate(
                    provider=webhook_event.provider,
                    event_type=webhook_event.event_type,
                    event_id=webhook_event.event_id,
                    raw_payload=webhook_event.raw_payload,
                )
            )
            
            # Update webhook with processed data
            webhook_event.processed_payload = processed_data
            webhook_event.status = WebhookStatus.PROCESSED.value
            webhook_event.processed_at = datetime.utcnow()
            webhook_event.failure_reason = None
            
            # Update payment status if applicable
            await self._update_payment_from_webhook(webhook_event, processed_data)
            
            self.db.commit()
            self.db.refresh(webhook_event)
            
            return self._map_to_webhook_response(webhook_event)
            
        except Exception as e:
            # Update webhook status to failed
            webhook_event.status = WebhookStatus.FAILED.value
            webhook_event.failure_reason = str(e)
            webhook_event.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            raise WebhookProcessingError(f"Webhook retry failed: {e}")
    
    def list_webhooks(
        self,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[WebhookEventResponse]:
        """
        List webhook events with optional filtering.
        
        Args:
            provider: Filter by provider name
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of webhook events
        """
        query = self.db.query(WebhookEvent)
        
        if provider:
            query = query.filter(WebhookEvent.provider == provider)
        
        if status:
            query = query.filter(WebhookEvent.status == status)
        
        webhooks = query.order_by(WebhookEvent.received_at.desc()).offset(offset).limit(limit).all()
        
        return [self._map_to_webhook_response(webhook) for webhook in webhooks]
    
    def get_webhook(self, webhook_event_id: int) -> WebhookEventResponse:
        """
        Get webhook event by ID.
        
        Args:
            webhook_event_id: Webhook event ID
            
        Returns:
            Webhook event response
            
        Raises:
            WebhookServiceError: If webhook not found
        """
        webhook_event = self.db.query(WebhookEvent).filter(
            WebhookEvent.id == webhook_event_id
        ).first()
        
        if not webhook_event:
            raise WebhookServiceError(f"Webhook event {webhook_event_id} not found")
        
        return self._map_to_webhook_response(webhook_event)
    
    def _find_duplicate_webhook(self, provider: str, event_id: str) -> Optional[WebhookEvent]:
        """Find duplicate webhook event."""
        return self.db.query(WebhookEvent).filter(
            WebhookEvent.provider == provider,
            WebhookEvent.event_id == event_id
        ).first()
    
    def _extract_signature_from_headers(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract signature from HTTP headers."""
        signature_headers = [
            'x-signature',
            'x-webhook-signature',
            'signature',
            'webhook-signature',
            'x-hub-signature',
            'chapa-signature',
            'telebirr-signature',
        ]
        
        for header_name in signature_headers:
            if header_name in headers:
                return headers[header_name]
        
        return None
    
    async def _update_payment_from_webhook(
        self, 
        webhook_event: WebhookEvent, 
        processed_data: Dict[str, Any]
    ) -> None:
        """
        Update payment status based on webhook data.
        
        Args:
            webhook_event: Webhook event record
            processed_data: Processed webhook data from provider
        """
        # Extract payment information from processed data
        provider_transaction_id = processed_data.get('provider_transaction_id')
        status = processed_data.get('status')
        amount = processed_data.get('amount')
        
        if not provider_transaction_id or not status:
            return  # No payment information to update
        
        # Find payment transaction
        transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.provider_transaction_id == provider_transaction_id
        ).first()
        
        if not transaction:
            return  # Transaction not found
        
        # Map webhook status to payment status
        status_mapping = {
            'completed': PaymentStatus.COMPLETED.value,
            'success': PaymentStatus.COMPLETED.value,
            'failed': PaymentStatus.FAILED.value,
            'cancelled': PaymentStatus.CANCELLED.value,
            'pending': PaymentStatus.PENDING.value,
            'processing': PaymentStatus.PROCESSING.value,
        }
        
        mapped_status = status_mapping.get(status)
        if not mapped_status:
            return  # Unknown status
        
        # Update transaction status
        old_status = transaction.status
        transaction.status = mapped_status
        transaction.processed_at = datetime.utcnow()
        transaction.provider_response = processed_data
        
        # Update payment intent status
        payment_intent = self.db.query(PaymentIntent).filter(
            PaymentIntent.id == transaction.payment_intent_id
        ).first()
        
        if payment_intent:
            payment_intent.status = mapped_status
            payment_intent.updated_at = datetime.utcnow()
            
            if mapped_status == PaymentStatus.COMPLETED.value:
                payment_intent.completed_at = datetime.utcnow()
            
            # Log status change
            self._log_payment_status_change(
                payment_intent.id,
                old_status,
                mapped_status,
                f"Webhook update from {webhook_event.provider}"
            )
    
    def _log_payment_status_change(
        self, 
        payment_intent_id: int, 
        old_status: str, 
        new_status: str, 
        reason: str
    ) -> None:
        """
        Log payment status change for audit trail.
        
        Args:
            payment_intent_id: Payment intent ID
            old_status: Previous status
            new_status: New status
            reason: Reason for change
        """
        # In a real implementation, this would create an audit log entry
        # For now, we'll just print it (in production, use proper logging)
        print(f"Payment {payment_intent_id} status changed: {old_status} -> {new_status} ({reason})")
    
    def _map_to_webhook_response(self, webhook_event: WebhookEvent) -> WebhookEventResponse:
        """Map WebhookEvent model to response schema."""
        return WebhookEventResponse(
            id=webhook_event.id,
            payment_intent_id=webhook_event.payment_intent_id,
            provider=webhook_event.provider,
            event_type=webhook_event.event_type,
            event_id=webhook_event.event_id,
            raw_payload=webhook_event.raw_payload,
            processed_payload=webhook_event.processed_payload,
            status=webhook_event.status,
            processing_attempts=webhook_event.processing_attempts,
            failure_reason=webhook_event.failure_reason,
            signature_verified=webhook_event.signature_verified,
            signature_verification_result=webhook_event.signature_verification_result,
            received_at=webhook_event.received_at,
            processed_at=webhook_event.processed_at,
        )
