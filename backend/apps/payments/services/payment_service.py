"""
Payment service - core business logic for payment processing.

This service handles payment operations with proper error handling,
idempotency, and security controls.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from apps.payments.models import (
    PaymentIntent,
    PaymentTransaction,
    Refund,
    WebhookEvent,
    PaymentStatus,
    TransactionType,
    WebhookStatus,
)
from apps.payments.providers.base import BasePaymentProvider, PaymentProcessingError
from apps.payments.schemas import (
    PaymentIntentCreate,
    PaymentIntentUpdate,
    PaymentProcessRequest,
    PaymentProcessResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    RefundCreate,
    PaymentIntentResponse,
    PaymentTransactionResponse,
)
from shared.db import get_db


class PaymentServiceError(Exception):
    """Base exception for payment service errors."""
    pass


class IdempotencyError(PaymentServiceError):
    """Raised when idempotency key is already used."""
    pass


class PaymentNotFoundError(PaymentServiceError):
    """Raised when payment is not found."""
    pass


class InvalidPaymentStatusError(PaymentServiceError):
    """Raised when payment status is invalid for operation."""
    pass


class PaymentService:
    """
    Core payment service with security, idempotency, and proper error handling.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._providers: Dict[str, BasePaymentProvider] = {}
    
    def register_provider(self, provider: BasePaymentProvider) -> None:
        """Register a payment provider."""
        self._providers[provider.get_provider_name()] = provider
    
    def get_provider(self, provider_name: str) -> BasePaymentProvider:
        """Get a registered payment provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            raise PaymentServiceError(f"Provider {provider_name} not registered")
        return provider
    
    def list_providers(self) -> List[str]:
        """List all registered providers."""
        return list(self._providers.keys())
    
    async def create_payment_intent(
        self, 
        request: PaymentIntentCreate,
        idempotency_key: Optional[str] = None
    ) -> PaymentIntentResponse:
        """
        Create a new payment intent with idempotency protection.
        
        Args:
            request: Payment intent creation request
            idempotency_key: Optional idempotency key for duplicate prevention
            
        Returns:
            Created payment intent
            
        Raises:
            IdempotencyError: If idempotency key already used
            PaymentServiceError: If creation fails
        """
        # Check idempotency
        if idempotency_key:
            existing_intent = self._find_intent_by_idempotency_key(idempotency_key)
            if existing_intent:
                raise IdempotencyError(f"Idempotency key {idempotency_key} already used")
        
        try:
            # Create payment intent
            payment_intent = PaymentIntent(
                app_name=request.app_name,
                object_type=request.object_type,
                object_id=request.object_id,
                amount=request.amount,
                currency=request.currency,
                description=request.description,
                customer_id=request.customer_id,
                merchant_id=request.merchant_id,
                preferred_provider=request.preferred_provider.value if request.preferred_provider else None,
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                webhook_url=request.webhook_url,
                metadata=request.metadata or {},
                expires_at=request.expires_at,
                status=PaymentStatus.PENDING.value,
            )
            
            # Store idempotency key if provided
            if idempotency_key:
                payment_intent.metadata['_idempotency_key'] = idempotency_key
            
            self.db.add(payment_intent)
            self.db.commit()
            self.db.refresh(payment_intent)
            
            return self._map_to_intent_response(payment_intent)
            
        except Exception as e:
            self.db.rollback()
            raise PaymentServiceError(f"Failed to create payment intent: {e}")
    
    async def process_payment(
        self, 
        request: PaymentProcessRequest,
        idempotency_key: Optional[str] = None
    ) -> PaymentProcessResponse:
        """
        Process a payment through the appropriate provider.
        
        Args:
            request: Payment processing request
            idempotency_key: Optional idempotency key
            
        Returns:
            Payment processing response
            
        Raises:
            PaymentNotFoundError: If payment intent not found
            InvalidPaymentStatusError: If payment is not in processable state
            PaymentServiceError: If processing fails
        """
        # Get payment intent
        payment_intent = self._get_payment_intent(request.payment_intent_id)
        
        # Check if payment can be processed
        if payment_intent.status not in [PaymentStatus.PENDING.value]:
            raise InvalidPaymentStatusError(
                f"Payment intent {payment_intent.id} has status {payment_intent.status}, cannot process"
            )
        
        # Check if payment has expired
        if payment_intent.expires_at and payment_intent.expires_at < datetime.utcnow():
            payment_intent.status = PaymentStatus.CANCELLED.value
            self.db.commit()
            raise InvalidPaymentStatusError("Payment intent has expired")
        
        # Check idempotency
        if idempotency_key:
            existing_transaction = self._find_transaction_by_idempotency_key(idempotency_key)
            if existing_transaction:
                return self._reconstruct_process_response(existing_transaction)
        
        # Select provider
        provider_name = request.provider or payment_intent.preferred_provider
        if not provider_name:
            raise PaymentServiceError("No provider specified and no preferred provider set")
        
        provider = self.get_provider(provider_name)
        
        try:
            # Process payment through provider
            process_response = await provider.initialize_payment(request)
            
            # Create transaction record
            transaction = PaymentTransaction(
                payment_intent_id=payment_intent.id,
                transaction_type=TransactionType.PAYMENT.value,
                amount=payment_intent.amount,
                currency=payment_intent.currency,
                provider=provider.get_provider_name(),
                provider_transaction_id=process_response.transaction.get('transaction_id'),
                provider_response=process_response.provider_response,
                status=PaymentStatus.PROCESSING.value,
                net_amount=payment_intent.amount,  # Will be updated after fees
                metadata={
                    'idempotency_key': idempotency_key,
                    'next_action': process_response.next_action,
                    'redirect_url': process_response.redirect_url,
                }
            )
            
            self.db.add(transaction)
            
            # Update payment intent status
            payment_intent.status = PaymentStatus.PROCESSING.value
            payment_intent.provider_transaction_id = transaction.provider_transaction_id
            payment_intent.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(transaction)
            self.db.refresh(payment_intent)
            
            return process_response
            
        except PaymentProcessingError as e:
            # Update payment intent status to failed
            payment_intent.status = PaymentStatus.FAILED.value
            payment_intent.updated_at = datetime.utcnow()
            
            # Create failed transaction record
            transaction = PaymentTransaction(
                payment_intent_id=payment_intent.id,
                transaction_type=TransactionType.PAYMENT.value,
                amount=payment_intent.amount,
                currency=payment_intent.currency,
                provider=provider.get_provider_name(),
                provider_response={'error': str(e)},
                status=PaymentStatus.FAILED.value,
                failure_reason=str(e),
                net_amount=Decimal('0'),
                metadata={'idempotency_key': idempotency_key}
            )
            
            self.db.add(transaction)
            self.db.commit()
            
            raise PaymentServiceError(f"Payment processing failed: {e}")
        
        except Exception as e:
            self.db.rollback()
            raise PaymentServiceError(f"Unexpected error during payment processing: {e}")
    
    async def verify_payment(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify payment status with provider.
        
        Args:
            request: Payment verification request
            
        Returns:
            Payment verification response
            
        Raises:
            PaymentNotFoundError: If payment intent not found
            PaymentServiceError: If verification fails
        """
        payment_intent = self._get_payment_intent(request.payment_intent_id)
        
        # Get the latest transaction for this payment intent
        transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.payment_intent_id == payment_intent.id
        ).order_by(PaymentTransaction.created_at.desc()).first()
        
        if not transaction:
            raise PaymentServiceError(f"No transaction found for payment intent {payment_intent.id}")
        
        # Get provider
        provider = self.get_provider(transaction.provider)
        
        try:
            # Verify payment with provider
            verify_response = await provider.verify_payment(request)
            
            # Update transaction status based on verification
            if verify_response.is_verified:
                transaction.status = PaymentStatus.COMPLETED.value
                payment_intent.status = PaymentStatus.COMPLETED.value
                payment_intent.completed_at = datetime.utcnow()
            else:
                transaction.status = PaymentStatus.FAILED.value
                payment_intent.status = PaymentStatus.FAILED.value
            
            transaction.processed_at = datetime.utcnow()
            transaction.provider_response = verify_response.verification_details
            transaction.updated_at = datetime.utcnow()
            payment_intent.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(transaction)
            self.db.refresh(payment_intent)
            
            return verify_response
            
        except Exception as e:
            self.db.rollback()
            raise PaymentServiceError(f"Payment verification failed: {e}")
    
    async def create_refund(
        self, 
        request: RefundCreate
    ) -> Refund:
        """
        Create a refund for a payment transaction.
        
        Args:
            request: Refund creation request
            
        Returns:
            Created refund
            
        Raises:
            PaymentNotFoundError: If original transaction not found
            InvalidPaymentStatusError: If transaction cannot be refunded
            PaymentServiceError: If refund creation fails
        """
        # Get original transaction
        original_transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.id == request.original_transaction_id
        ).first()
        
        if not original_transaction:
            raise PaymentNotFoundError(f"Original transaction {request.original_transaction_id} not found")
        
        if original_transaction.status != PaymentStatus.COMPLETED.value:
            raise InvalidPaymentStatusError(
                f"Cannot refund transaction with status {original_transaction.status}"
            )
        
        # Check if refund amount exceeds original amount
        total_refunded = self.db.query(Refund).filter(
            Refund.original_transaction_id == original_transaction.id,
            Refund.status == PaymentStatus.COMPLETED.value
        ).with_entities(Refund.amount).all()
        
        total_refunded_amount = sum(refund.amount for refund in total_refunded)
        
        if total_refunded_amount + request.amount > original_transaction.amount:
            raise InvalidPaymentStatusError("Refund amount exceeds original transaction amount")
        
        try:
            # Create refund record
            refund = Refund(
                original_transaction_id=request.original_transaction_id,
                amount=request.amount,
                currency=request.currency,
                reason=request.reason,
                status=PaymentStatus.PENDING.value,
                metadata=request.metadata or {},
                refunded_by=request.refunded_by,
            )
            
            self.db.add(refund)
            self.db.commit()
            self.db.refresh(refund)
            
            # Process refund through provider
            provider = self.get_provider(original_transaction.provider)
            refund_response = await provider.refund_payment(request)
            
            # Update refund with provider response
            refund.provider_refund_id = refund_response.get('refund_id')
            refund.provider_response = refund_response
            refund.status = PaymentStatus.PROCESSING.value
            refund.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(refund)
            
            return refund
            
        except Exception as e:
            self.db.rollback()
            raise PaymentServiceError(f"Refund creation failed: {e}")
    
    def get_payment_intent(
        self, 
        payment_intent_id: int
    ) -> PaymentIntentResponse:
        """
        Get payment intent by ID.
        
        Args:
            payment_intent_id: Payment intent ID
            
        Returns:
            Payment intent response
            
        Raises:
            PaymentNotFoundError: If payment intent not found
        """
        payment_intent = self._get_payment_intent(payment_intent_id)
        return self._map_to_intent_response(payment_intent)
    
    def list_payment_intents(
        self, 
        app_name: Optional[str] = None,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PaymentIntentResponse]:
        """
        List payment intents with optional filtering.
        
        Args:
            app_name: Filter by app name
            customer_id: Filter by customer ID
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of payment intents
        """
        query = self.db.query(PaymentIntent)
        
        if app_name:
            query = query.filter(PaymentIntent.app_name == app_name)
        
        if customer_id:
            query = query.filter(PaymentIntent.customer_id == customer_id)
        
        if status:
            query = query.filter(PaymentIntent.status == status)
        
        payment_intents = query.order_by(PaymentIntent.created_at.desc()).offset(offset).limit(limit).all()
        
        return [self._map_to_intent_response(intent) for intent in payment_intents]
    
    def _get_payment_intent(self, payment_intent_id: int) -> PaymentIntent:
        """Get payment intent by ID, raise if not found."""
        payment_intent = self.db.query(PaymentIntent).filter(
            PaymentIntent.id == payment_intent_id
        ).first()
        
        if not payment_intent:
            raise PaymentNotFoundError(f"Payment intent {payment_intent_id} not found")
        
        return payment_intent
    
    def _find_intent_by_idempotency_key(self, idempotency_key: str) -> Optional[PaymentIntent]:
        """Find payment intent by idempotency key."""
        return self.db.query(PaymentIntent).filter(
            PaymentIntent.metadata['_idempotency_key'].astext == idempotency_key
        ).first()
    
    def _find_transaction_by_idempotency_key(self, idempotency_key: str) -> Optional[PaymentTransaction]:
        """Find transaction by idempotency key."""
        return self.db.query(PaymentTransaction).filter(
            PaymentTransaction.metadata['_idempotency_key'].astext == idempotency_key
        ).first()
    
    def _reconstruct_process_response(self, transaction: PaymentTransaction) -> PaymentProcessResponse:
        """Reconstruct payment process response from existing transaction."""
        # This would need to get the original payment intent
        payment_intent = self.db.query(PaymentIntent).filter(
            PaymentIntent.id == transaction.payment_intent_id
        ).first()
        
        return PaymentProcessResponse(
            payment_intent=self._map_to_intent_response(payment_intent),
            transaction=self._map_to_transaction_response(transaction),
            provider_response=transaction.provider_response,
            next_action=transaction.metadata.get('next_action'),
            redirect_url=transaction.metadata.get('redirect_url')
        )
    
    def _map_to_intent_response(self, payment_intent: PaymentIntent) -> PaymentIntentResponse:
        """Map PaymentIntent model to response schema."""
        return PaymentIntentResponse(
            id=payment_intent.id,
            app_name=payment_intent.app_name,
            object_type=payment_intent.object_type,
            object_id=payment_intent.object_id,
            amount=payment_intent.amount,
            currency=payment_intent.currency,
            description=payment_intent.description,
            customer_id=payment_intent.customer_id,
            merchant_id=payment_intent.merchant_id,
            status=payment_intent.status,
            metadata=payment_intent.metadata,
            preferred_provider=payment_intent.preferred_provider,
            provider_transaction_id=payment_intent.provider_transaction_id,
            success_url=payment_intent.success_url,
            cancel_url=payment_intent.cancel_url,
            webhook_url=payment_intent.webhook_url,
            created_at=payment_intent.created_at,
            updated_at=payment_intent.updated_at,
            expires_at=payment_intent.expires_at,
            completed_at=payment_intent.completed_at,
        )
    
    def _map_to_transaction_response(self, transaction: PaymentTransaction) -> PaymentTransactionResponse:
        """Map PaymentTransaction model to response schema."""
        return PaymentTransactionResponse(
            id=transaction.id,
            payment_intent_id=transaction.payment_intent_id,
            transaction_type=transaction.transaction_type,
            amount=transaction.amount,
            currency=transaction.currency,
            provider=transaction.provider,
            provider_transaction_id=transaction.provider_transaction_id,
            provider_response=transaction.provider_response,
            status=transaction.status,
            failure_reason=transaction.failure_reason,
            provider_fee=transaction.provider_fee,
            platform_fee=transaction.platform_fee,
            net_amount=transaction.net_amount,
            metadata=transaction.metadata,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
            processed_at=transaction.processed_at,
        )
