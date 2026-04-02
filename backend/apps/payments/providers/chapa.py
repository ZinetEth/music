"""
Chapa payment provider implementation.

Chapa is an Ethiopian payment aggregator that supports multiple
payment methods including bank transfers, mobile money, and cards.
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


class ChapaProvider(BasePaymentProvider):
    """
    Chapa payment provider implementation.
    
    Handles payments through Chapa's payment gateway API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.chapa.co')
        self.secret_key = config.get('secret_key')
        self.webhook_secret = config.get('webhook_secret')
        self.merchant_id = config.get('merchant_id')
    
    def validate_config(self) -> None:
        """Validate Chapa configuration."""
        required_fields = ['secret_key', 'webhook_secret', 'merchant_id']
        
        for field in required_fields:
            if not self.config.get(field):
                raise ProviderConfigurationError(f"Chapa requires {field} in configuration")
        
        # Validate URL format
        if not self.base_url.startswith('https://'):
            raise ProviderConfigurationError("Chapa base URL must use HTTPS")
    
    async def initialize_payment(
        self, 
        request: PaymentProcessRequest
    ) -> PaymentProcessResponse:
        """
        Initialize Chapa payment.
        
        Chapa provides a checkout URL where customers can complete payment.
        """
        # Validate amount and currency
        self.validate_amount(request.payment_intent.amount)
        self.validate_currency(request.payment_intent.currency)
        
        # Generate transaction reference
        transaction_ref = self._generate_transaction_ref(request.payment_intent.id)
        
        # Prepare payment data
        payment_data = {
            'amount': str(request.payment_intent.amount),
            'currency': request.payment_intent.currency,
            'email': f"customer_{request.payment_intent.customer_id}@example.com",  # Would be from customer data
            'first_name': 'Customer',
            'last_name': str(request.payment_intent.customer_id),
            'tx_ref': transaction_ref,
            'callback_url': request.payment_intent.webhook_url,
            'return_url': request.payment_intent.success_url or '',
            'customization': {
                'title': request.payment_intent.description or 'Payment',
                'description': f"Payment for {request.payment_intent.object_type}:{request.payment_intent.object_id}",
            },
            'meta': {
                'payment_intent_id': request.payment_intent.id,
                'app_name': request.payment_intent.app_name,
                'object_type': request.payment_intent.object_type,
                'object_id': request.payment_intent.object_id,
                'customer_id': request.payment_intent.customer_id,
                'merchant_id': request.payment_intent.merchant_id,
            }
        }
        
        try:
            # Make API call to Chapa
            response = await self._make_chapa_request('/v1/transaction/initialize', payment_data)
            
            if not response.get('status') or response.get('status') != 'success':
                raise PaymentProcessingError(
                    f"Chapa payment initialization failed: {response.get('message', 'Unknown error')}"
                )
            
            # Return payment process response
            return PaymentProcessResponse(
                payment_intent=request.payment_intent,
                transaction={
                    'tx_ref': transaction_ref,
                    'checkout_url': response.get('data', {}).get('checkout_url'),
                },
                provider_response=response,
                next_action='redirect',
                redirect_url=response.get('data', {}).get('checkout_url')
            )
            
        except Exception as e:
            raise PaymentProcessingError(f"Chapa API error: {e}")
    
    async def verify_payment(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify Chapa payment status.
        
        Chapa payments are verified by checking the transaction status.
        """
        verification_data = {
            'tx_ref': request.provider_transaction_id,
        }
        
        try:
            response = await self._make_chapa_request('/v1/transaction/verify', verification_data)
            
            if not response.get('status') or response.get('status') != 'success':
                return PaymentVerifyResponse(
                    payment_intent=request.payment_intent,
                    transaction={'tx_ref': request.provider_transaction_id},
                    is_verified=False,
                    verification_details={'error': response.get('message', 'Unknown error')}
                )
            
            transaction_data = response.get('data', {})
            transaction_status = transaction_data.get('status', 'unknown')
            is_verified = transaction_status == 'success'
            
            return PaymentVerifyResponse(
                payment_intent=request.payment_intent,
                transaction=transaction_data,
                is_verified=is_verified,
                verification_details={
                    'status': transaction_status,
                    'amount': transaction_data.get('amount'),
                    'currency': transaction_data.get('currency'),
                    'paid_at': transaction_data.get('created_at'),
                    'payment_method': transaction_data.get('payment_method'),
                }
            )
            
        except Exception as e:
            raise PaymentProcessingError(f"Chapa verification error: {e}")
    
    async def process_webhook(
        self, 
        webhook_data: WebhookEventCreate
    ) -> Dict[str, Any]:
        """
        Process Chapa webhook.
        
        Chapa sends payment status updates via webhooks.
        """
        payload = webhook_data.raw_payload
        
        # Verify webhook signature
        if not self._verify_webhook_signature(payload):
            raise WebhookVerificationError("Invalid Chapa webhook signature")
        
        # Extract payment information
        tx_ref = payload.get('tx_ref')
        status = payload.get('status')
        amount = payload.get('amount')
        
        if not tx_ref or not status:
            raise WebhookVerificationError("Missing required webhook fields")
        
        # Map Chapa status to our status
        status_mapping = {
            'success': 'completed',
            'failed': 'failed',
            'pending': 'pending',
            'cancelled': 'cancelled',
        }
        
        mapped_status = status_mapping.get(status, 'pending')
        
        return {
            'provider_transaction_id': tx_ref,
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
        Process Chapa refund.
        
        Chapa supports refunds through their API.
        """
        refund_data = {
            'tx_ref': f"refund_{refund_request.original_transaction_id}_{int(datetime.utcnow().timestamp())}",
            'amount': str(refund_request.amount),
            'reason': refund_request.reason or 'Customer refund',
        }
        
        try:
            response = await self._make_chapa_request('/v1/transaction/refund', refund_data)
            
            if not response.get('status') or response.get('status') != 'success':
                raise PaymentProcessingError(
                    f"Chapa refund failed: {response.get('message', 'Unknown error')}"
                )
            
            return {
                'refund_id': response.get('data', {}).get('tx_ref'),
                'status': 'pending',
                'provider_response': response,
            }
            
        except Exception as e:
            raise PaymentProcessingError(f"Chapa refund error: {e}")
    
    def verify_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify Chapa webhook signature.
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
        Get payment status from Chapa.
        """
        # This would be implemented to check status via API
        return {
            'tx_ref': provider_transaction_id,
            'status': 'unknown',
            'checked_at': datetime.utcnow().isoformat(),
        }
    
    def _generate_transaction_ref(self, payment_intent_id: int) -> str:
        """Generate unique transaction reference."""
        timestamp = int(datetime.utcnow().timestamp())
        return f"music_{payment_intent_id}_{timestamp}"
    
    def _verify_webhook_signature(self, payload: Dict[str, Any]) -> bool:
        """
        Verify Chapa webhook signature.
        
        Chapa uses HMAC-SHA256 with webhook secret.
        """
        received_signature = payload.get('signature')
        if not received_signature:
            return False
        
        # Create string to sign
        payload_copy = payload.copy()
        payload_copy.pop('signature', None)
        
        # Sort and join payload
        sorted_payload = sorted(payload_copy.items())
        string_to_sign = '&'.join([f"{k}={v}" for k, v in sorted_payload])
        
        # Generate expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(received_signature, expected_signature)
    
    async def _make_chapa_request(
        self, 
        endpoint: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Chapa API.
        """
        import httpx
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'MusicPlatform/1.0',
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "chapa"
    
    def get_supported_currencies(self) -> list[str]:
        """Get supported currencies."""
        return ['ETB', 'USD']
    
    def get_minimum_amount(self) -> Decimal:
        """Get minimum amount."""
        return Decimal('1.00')  # 1 ETB minimum
    
    def get_maximum_amount(self) -> Decimal:
        """Get maximum amount."""
        return Decimal('100000.00')  # 100,000 ETB maximum
