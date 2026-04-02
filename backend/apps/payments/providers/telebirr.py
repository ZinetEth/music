"""
Telebirr payment provider implementation.

Telebirr is Ethiopia's mobile money service provided by Ethio Telecom.
This provider handles Telebirr-specific payment processing and webhooks.
"""

import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from apps.payments.providers.base import (
    BasePaymentProvider,
    PaymentProcessingError,
    ProviderConfigurationError,
    WebhookVerificationError,
)
from apps.payments.schemas import (
    PaymentProcessRequest,
    PaymentProcessResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    WebhookEventCreate,
    RefundCreate,
)


class TelebirrProvider(BasePaymentProvider):
    """
    Telebirr payment provider implementation.
    
    Handles mobile money payments through Telebirr's API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.telebirr.et')
        self.app_id = config.get('app_id')
        self.app_secret = config.get('app_secret')
        self.merchant_code = config.get('merchant_code')
        self.short_code = config.get('short_code')
    
    def validate_config(self) -> None:
        """Validate Telebirr configuration."""
        required_fields = ['app_id', 'app_secret', 'merchant_code', 'short_code']
        
        for field in required_fields:
            if not self.config.get(field):
                raise ProviderConfigurationError(f"Telebirr requires {field} in configuration")
        
        # Validate URL format
        if not self.base_url.startswith('https://'):
            raise ProviderConfigurationError("Telebirr base URL must use HTTPS")
    
    async def initialize_payment(
        self, 
        request: PaymentProcessRequest
    ) -> PaymentProcessResponse:
        """
        Initialize Telebirr payment.
        
        Telebirr uses USSD-based payment flow where customers receive
        a prompt on their mobile phones to confirm payment.
        """
        # Validate amount and currency
        self.validate_amount(request.payment_intent.amount)
        self.validate_currency(request.payment_intent.currency)
        
        # Generate Telebirr payment request
        payment_data = {
            'app_id': self.app_id,
            'merchant_code': self.merchant_code,
            'short_code': self.short_code,
            'amount': float(request.payment_intent.amount),
            'currency': request.payment_intent.currency,
            'description': request.payment_intent.description or 'Payment',
            'callback_url': request.payment_intent.webhook_url,
            'nonce': self._generate_nonce(),
            'timestamp': int(datetime.utcnow().timestamp()),
        }
        
        # Generate signature
        signature = self._generate_signature(payment_data)
        payment_data['signature'] = signature
        
        try:
            # Make API call to Telebirr
            response = await self._make_telebirr_request('/payment/initiate', payment_data)
            
            if response.get('status') != 'success':
                raise PaymentProcessingError(
                    f"Telebirr payment initialization failed: {response.get('message', 'Unknown error')}"
                )
            
            # Return payment process response
            return PaymentProcessResponse(
                payment_intent=request.payment_intent,
                transaction=response.get('transaction', {}),
                provider_response=response,
                next_action='ussd_prompt',
                redirect_url=None
            )
            
        except Exception as e:
            raise PaymentProcessingError(f"Telebirr API error: {e}")
    
    async def verify_payment(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify Telebirr payment status.
        
        Telebirr payments are verified by checking the transaction status
        with Telebirr's API.
        """
        verification_data = {
            'app_id': self.app_id,
            'merchant_code': self.merchant_code,
            'transaction_id': request.provider_transaction_id,
            'nonce': self._generate_nonce(),
            'timestamp': int(datetime.utcnow().timestamp()),
        }
        
        signature = self._generate_signature(verification_data)
        verification_data['signature'] = signature
        
        try:
            response = await self._make_telebirr_request('/payment/status', verification_data)
            
            if response.get('status') != 'success':
                return PaymentVerifyResponse(
                    payment_intent=request.payment_intent,
                    transaction=response.get('transaction', {}),
                    is_verified=False,
                    verification_details={'error': response.get('message', 'Unknown error')}
                )
            
            transaction_status = response.get('transaction', {}).get('status', 'unknown')
            is_verified = transaction_status in ['completed', 'success']
            
            return PaymentVerifyResponse(
                payment_intent=request.payment_intent,
                transaction=response.get('transaction', {}),
                is_verified=is_verified,
                verification_details={
                    'status': transaction_status,
                    'paid_amount': response.get('transaction', {}).get('amount'),
                    'paid_at': response.get('transaction', {}).get('completed_at'),
                }
            )
            
        except Exception as e:
            raise PaymentProcessingError(f"Telebirr verification error: {e}")
    
    async def process_webhook(
        self, 
        webhook_data: WebhookEventCreate
    ) -> Dict[str, Any]:
        """
        Process Telebirr webhook.
        
        Telebirr sends payment status updates via webhooks.
        """
        payload = webhook_data.raw_payload
        
        # Verify webhook signature
        if not self._verify_webhook_signature(payload):
            raise WebhookVerificationError("Invalid Telebirr webhook signature")
        
        # Extract payment information
        transaction_id = payload.get('transaction_id')
        status = payload.get('status')
        amount = payload.get('amount')
        
        if not transaction_id or not status:
            raise WebhookVerificationError("Missing required webhook fields")
        
        # Map Telebirr status to our status
        status_mapping = {
            'success': 'completed',
            'failed': 'failed',
            'pending': 'pending',
            'cancelled': 'cancelled',
        }
        
        mapped_status = status_mapping.get(status, 'pending')
        
        return {
            'provider_transaction_id': transaction_id,
            'status': mapped_status,
            'amount': Decimal(str(amount)) if amount else None,
            'processed_at': datetime.utcnow().isoformat(),
            'webhook_data': payload,
        }
    
    async def refund_payment(
        self, 
        refund_request: RefundCreate
    ) -> Dict[str, Any]:
        """
        Process Telebirr refund.
        
        Note: Telebirr refunds may require manual approval or
        may not be supported depending on the merchant agreement.
        """
        refund_data = {
            'app_id': self.app_id,
            'merchant_code': self.merchant_code,
            'original_transaction_id': refund_request.original_transaction_id,
            'refund_amount': float(refund_request.amount),
            'reason': refund_request.reason or 'Customer refund',
            'nonce': self._generate_nonce(),
            'timestamp': int(datetime.utcnow().timestamp()),
        }
        
        signature = self._generate_signature(refund_data)
        refund_data['signature'] = signature
        
        try:
            response = await self._make_telebirr_request('/payment/refund', refund_data)
            
            if response.get('status') != 'success':
                raise PaymentProcessingError(
                    f"Telebirr refund failed: {response.get('message', 'Unknown error')}"
                )
            
            return {
                'refund_id': response.get('refund_id'),
                'status': 'pending',
                'provider_response': response,
            }
            
        except Exception as e:
            raise PaymentProcessingError(f"Telebirr refund error: {e}")
    
    def verify_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify Telebirr webhook signature.
        """
        try:
            payload_data = json.loads(payload)
            return self._verify_webhook_signature(payload_data)
        except json.JSONDecodeError:
            return False
    
    def get_payment_status(
        self, 
        provider_transaction_id: str
    ) -> Dict[str, Any]:
        """
        Get payment status from Telebirr.
        """
        # This would be implemented to check status via API
        # For now, return placeholder
        return {
            'transaction_id': provider_transaction_id,
            'status': 'unknown',
            'checked_at': datetime.utcnow().isoformat(),
        }
    
    def _generate_nonce(self) -> str:
        """Generate nonce for Telebirr API."""
        import secrets
        return secrets.token_hex(16)
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        Generate Telebirr signature.
        
        Telebirr uses HMAC-SHA256 for signature generation.
        """
        # Sort data for consistent signature
        sorted_data = sorted(data.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_data if k != 'signature'])
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _verify_webhook_signature(self, payload: Dict[str, Any]) -> bool:
        """
        Verify Telebirr webhook signature.
        """
        received_signature = payload.get('signature')
        if not received_signature:
            return False
        
        # Remove signature from payload for verification
        payload_copy = payload.copy()
        payload_copy.pop('signature', None)
        
        # Generate expected signature
        expected_signature = self._generate_signature(payload_copy)
        
        # Compare signatures
        return hmac.compare_digest(received_signature, expected_signature)
    
    async def _make_telebirr_request(
        self, 
        endpoint: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Telebirr API.
        
        This is a placeholder implementation. In production,
        you would use proper HTTP client with retry logic.
        """
        import httpx
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MusicPlatform/1.0',
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "telebirr"
    
    def get_supported_currencies(self) -> list[str]:
        """Get supported currencies."""
        return ['ETB']
    
    def get_minimum_amount(self) -> Decimal:
        """Get minimum amount."""
        return Decimal('1.00')  # 1 ETB minimum
    
    def get_maximum_amount(self) -> Decimal:
        """Get maximum amount."""
        return Decimal('10000.00')  # 10,000 ETB maximum
