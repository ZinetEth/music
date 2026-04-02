"""
Base payment provider interface.

All payment providers must implement this interface to ensure
consistency and reusability across the payment system.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from apps.payments.schemas import (
    PaymentProcessRequest,
    PaymentProcessResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    WebhookEventCreate,
    RefundCreate,
)


class PaymentProviderError(Exception):
    """Base exception for payment provider errors."""
    
    def __init__(self, message: str, error_code: str = None, provider_data: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.provider_data = provider_data or {}
        super().__init__(message)


class ProviderConfigurationError(PaymentProviderError):
    """Raised when provider configuration is invalid."""
    pass


class PaymentProcessingError(PaymentProviderError):
    """Raised when payment processing fails."""
    pass


class WebhookVerificationError(PaymentProviderError):
    """Raised when webhook verification fails."""
    pass


class BasePaymentProvider(ABC):
    """
    Base interface for all payment providers.
    
    This interface ensures that all providers implement the same
    set of operations, making the payment system provider-agnostic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.validate_config()
    
    @abstractmethod
    def validate_config(self) -> None:
        """
        Validate provider configuration.
        
        Raises:
            ProviderConfigurationError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    async def initialize_payment(
        self, 
        request: PaymentProcessRequest
    ) -> PaymentProcessResponse:
        """
        Initialize a payment with the provider.
        
        Args:
            request: Payment processing request
            
        Returns:
            Payment process response with provider-specific details
            
        Raises:
            PaymentProcessingError: If payment initialization fails
        """
        pass
    
    @abstractmethod
    async def verify_payment(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify a payment status with the provider.
        
        Args:
            request: Payment verification request
            
        Returns:
            Payment verification response
            
        Raises:
            PaymentProcessingError: If verification fails
        """
        pass
    
    @abstractmethod
    async def process_webhook(
        self, 
        webhook_data: WebhookEventCreate
    ) -> Dict[str, Any]:
        """
        Process a webhook event from the provider.
        
        Args:
            webhook_data: Webhook event data
            
        Returns:
            Processed webhook data
            
        Raises:
            WebhookVerificationError: If webhook verification fails
        """
        pass
    
    @abstractmethod
    async def refund_payment(
        self, 
        refund_request: RefundCreate
    ) -> Dict[str, Any]:
        """
        Process a refund with the provider.
        
        Args:
            refund_request: Refund request details
            
        Returns:
            Refund processing response
            
        Raises:
            PaymentProcessingError: If refund fails
        """
        pass
    
    @abstractmethod
    def verify_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            headers: HTTP headers
            
        Returns:
            True if signature is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_payment_status(
        self, 
        provider_transaction_id: str
    ) -> Dict[str, Any]:
        """
        Get payment status from provider.
        
        Args:
            provider_transaction_id: Provider's transaction ID
            
        Returns:
            Payment status information
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return self.__class__.__name__.replace('Provider', '').lower()
    
    def is_test_mode(self) -> bool:
        """Check if provider is in test mode."""
        return self.config.get('test_mode', False)
    
    def get_supported_currencies(self) -> list[str]:
        """Get list of supported currencies."""
        return self.config.get('supported_currencies', ['ETB'])
    
    def get_minimum_amount(self) -> Decimal:
        """Get minimum payment amount."""
        return Decimal(str(self.config.get('minimum_amount', '1.00')))
    
    def get_maximum_amount(self) -> Decimal:
        """Get maximum payment amount."""
        return Decimal(str(self.config.get('maximum_amount', '100000.00')))
    
    def validate_amount(self, amount: Decimal) -> None:
        """
        Validate payment amount.
        
        Args:
            amount: Payment amount to validate
            
        Raises:
            PaymentProcessingError: If amount is invalid
        """
        if amount < self.get_minimum_amount():
            raise PaymentProcessingError(
                f"Amount {amount} is below minimum {self.get_minimum_amount()}"
            )
        
        if amount > self.get_maximum_amount():
            raise PaymentProcessingError(
                f"Amount {amount} is above maximum {self.get_maximum_amount()}"
            )
    
    def validate_currency(self, currency: str) -> None:
        """
        Validate currency.
        
        Args:
            currency: Currency code to validate
            
        Raises:
            PaymentProcessingError: If currency is not supported
        """
        if currency not in self.get_supported_currencies():
            raise PaymentProcessingError(
                f"Currency {currency} is not supported. "
                f"Supported currencies: {self.get_supported_currencies()}"
            )


class BaseWebhookProcessor:
    """
    Base webhook processor for handling provider webhooks.
    """
    
    def __init__(self, provider: BasePaymentProvider):
        self.provider = provider
    
    async def process_webhook(
        self, 
        payload: str, 
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process incoming webhook.
        
        Args:
            payload: Raw webhook payload
            headers: HTTP headers
            
        Returns:
            Processed webhook data
            
        Raises:
            WebhookVerificationError: If webhook is invalid
        """
        # Extract signature from headers
        signature = self.extract_signature(headers)
        
        # Verify signature
        if not self.provider.verify_webhook_signature(payload, signature, headers):
            raise WebhookVerificationError("Invalid webhook signature")
        
        # Parse webhook data
        try:
            import json
            webhook_data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise WebhookVerificationError(f"Invalid webhook JSON: {e}")
        
        # Process webhook based on event type
        event_type = webhook_data.get('type', 'unknown')
        event_id = webhook_data.get('id', 'unknown')
        
        processed_data = {
            'event_type': event_type,
            'event_id': event_id,
            'provider': self.provider.get_provider_name(),
            'raw_payload': webhook_data,
            'processed_at': datetime.utcnow().isoformat(),
        }
        
        # Provider-specific processing
        try:
            provider_data = await self.provider.process_webhook(
                WebhookEventCreate(
                    provider=self.provider.get_provider_name(),
                    event_type=event_type,
                    event_id=event_id,
                    raw_payload=webhook_data
                )
            )
            processed_data.update(provider_data)
        except Exception as e:
            raise WebhookVerificationError(f"Provider processing failed: {e}")
        
        return processed_data
    
    def extract_signature(self, headers: Dict[str, str]) -> str:
        """
        Extract signature from headers.
        
        Args:
            headers: HTTP headers
            
        Returns:
            Signature string
        """
        # Common signature header names
        signature_headers = [
            'x-signature',
            'x-webhook-signature',
            'signature',
            'webhook-signature',
            'x-hub-signature',
        ]
        
        for header_name in signature_headers:
            if header_name in headers:
                return headers[header_name]
        
        raise WebhookVerificationError("No signature header found")
