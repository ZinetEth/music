"""
CBE (Commercial Bank of Ethiopia) payment provider implementation.

CBE provides bank transfer and digital banking services.
This provider handles manual bank transfer verification and CBE Birr integration.
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


class CBEBankProvider(BasePaymentProvider):
    """
    CBE Bank payment provider implementation.
    
    Handles manual bank transfer verification and CBE digital payments.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.cbe.com.et')
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.account_number = config.get('account_number')
        self.account_name = config.get('account_name')
        self.bank_code = config.get('bank_code', 'CBEET')
        self.manual_verification_enabled = config.get('manual_verification', True)
    
    def validate_config(self) -> None:
        """Validate CBE configuration."""
        required_fields = ['account_number', 'account_name']
        
        for field in required_fields:
            if not self.config.get(field):
                raise ProviderConfigurationError(f"CBE requires {field} in configuration")
        
        # For API integration, require API credentials
        if self.config.get('api_enabled', False):
            api_required = ['api_key', 'api_secret']
            for field in api_required:
                if not self.config.get(field):
                    raise ProviderConfigurationError(f"CBE API requires {field} in configuration")
    
    async def initialize_payment(
        self, 
        request: PaymentProcessRequest
    ) -> PaymentProcessResponse:
        """
        Initialize CBE payment.
        
        For manual bank transfers, generates payment instructions.
        For API integration, initiates digital payment.
        """
        # Validate amount and currency
        self.validate_amount(request.payment_intent.amount)
        self.validate_currency(request.payment_intent.currency)
        
        if self.manual_verification_enabled:
            # Manual bank transfer flow
            return await self._initialize_manual_transfer(request)
        else:
            # API-based payment flow
            return await self._initialize_digital_payment(request)
    
    async def _initialize_manual_transfer(
        self, 
        request: PaymentProcessRequest
    ) -> PaymentProcessResponse:
        """
        Initialize manual bank transfer payment.
        """
        # Generate unique reference
        reference = self._generate_bank_reference(request.payment_intent.id)
        
        # Create payment instructions
        payment_instructions = {
            'bank_name': 'Commercial Bank of Ethiopia',
            'account_number': self.account_number,
            'account_name': self.account_name,
            'amount': float(request.payment_intent.amount),
            'currency': request.payment_intent.currency,
            'reference': reference,
            'description': request.payment_intent.description or 'Payment',
            'payment_deadline': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }
        
        return PaymentProcessResponse(
            payment_intent=request.payment_intent,
            transaction={
                'reference': reference,
                'payment_instructions': payment_instructions,
                'verification_method': 'manual',
            },
            provider_response={'status': 'pending', 'reference': reference},
            next_action='manual_transfer',
            redirect_url=None
        )
    
    async def _initialize_digital_payment(
        self, 
        request: PaymentProcessRequest
    ) -> PaymentProcessResponse:
        """
        Initialize CBE digital payment.
        """
        if not self.api_key or not self.api_secret:
            raise PaymentProcessingError("CBE API credentials not configured")
        
        # Prepare payment data
        payment_data = {
            'account_number': self.account_number,
            'amount': float(request.payment_intent.amount),
            'currency': request.payment_intent.currency,
            'reference': self._generate_bank_reference(request.payment_intent.id),
            'description': request.payment_intent.description or 'Payment',
            'callback_url': request.payment_intent.webhook_url,
            'customer_id': request.payment_intent.customer_id,
        }
        
        # Generate signature
        signature = self._generate_signature(payment_data)
        payment_data['signature'] = signature
        
        try:
            # Make API call to CBE
            response = await self._make_cbe_request('/v1/payment/initiate', payment_data)
            
            if response.get('status') != 'success':
                raise PaymentProcessingError(
                    f"CBE payment initialization failed: {response.get('message', 'Unknown error')}"
                )
            
            return PaymentProcessResponse(
                payment_intent=request.payment_intent,
                transaction=response.get('payment', {}),
                provider_response=response,
                next_action='bank_redirect',
                redirect_url=response.get('payment', {}).get('redirect_url')
            )
            
        except Exception as e:
            raise PaymentProcessingError(f"CBE API error: {e}")
    
    async def verify_payment(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify CBE payment status.
        
        For manual transfers, checks admin verification.
        For digital payments, checks API status.
        """
        if self.manual_verification_enabled:
            return await self._verify_manual_transfer(request)
        else:
            return await self._verify_digital_payment(request)
    
    async def _verify_manual_transfer(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify manual bank transfer payment.
        
        Manual transfers require admin verification in the system.
        """
        # Check if payment has been manually verified by admin
        # This would typically check a database table or admin panel
        
        # For now, return pending status
        return PaymentVerifyResponse(
            payment_intent=request.payment_intent,
            transaction={'reference': request.provider_transaction_id},
            is_verified=False,
            verification_details={
                'status': 'pending_manual_verification',
                'message': 'Payment requires manual verification by admin',
                'verification_method': 'manual',
            }
        )
    
    async def _verify_digital_payment(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify CBE digital payment status.
        """
        verification_data = {
            'reference': request.provider_transaction_id,
        }
        
        try:
            response = await self._make_cbe_request('/v1/payment/status', verification_data)
            
            if response.get('status') != 'success':
                return PaymentVerifyResponse(
                    payment_intent=request.payment_intent,
                    transaction={'reference': request.provider_transaction_id},
                    is_verified=False,
                    verification_details={'error': response.get('message', 'Unknown error')}
                )
            
            payment_data = response.get('payment', {})
            payment_status = payment_data.get('status', 'unknown')
            is_verified = payment_status in ['completed', 'success']
            
            return PaymentVerifyResponse(
                payment_intent=request.payment_intent,
                transaction=payment_data,
                is_verified=is_verified,
                verification_details={
                    'status': payment_status,
                    'amount': payment_data.get('amount'),
                    'completed_at': payment_data.get('completed_at'),
                }
            )
            
        except Exception as e:
            raise PaymentProcessingError(f"CBE verification error: {e}")
    
    async def process_webhook(
        self, 
        webhook_data: WebhookEventCreate
    ) -> Dict[str, Any]:
        """
        Process CBE webhook.
        
        CBE sends payment status updates for digital payments.
        """
        payload = webhook_data.raw_payload
        
        # Verify webhook signature
        if not self._verify_webhook_signature(payload):
            raise WebhookVerificationError("Invalid CBE webhook signature")
        
        # Extract payment information
        reference = payload.get('reference')
        status = payload.get('status')
        amount = payload.get('amount')
        
        if not reference or not status:
            raise WebhookVerificationError("Missing required webhook fields")
        
        # Map CBE status to our status
        status_mapping = {
            'success': 'completed',
            'failed': 'failed',
            'pending': 'pending',
            'cancelled': 'cancelled',
        }
        
        mapped_status = status_mapping.get(status, 'pending')
        
        return {
            'provider_transaction_id': reference,
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
        Process CBE refund.
        
        For manual transfers, requires manual processing.
        For digital payments, uses API if available.
        """
        if self.manual_verification_enabled:
            return {
                'refund_id': f"manual_refund_{refund_request.original_transaction_id}",
                'status': 'pending_manual_processing',
                'message': 'Refund requires manual processing',
            }
        
        refund_data = {
            'original_reference': refund_request.original_transaction_id,
            'refund_amount': float(refund_request.amount),
            'reason': refund_request.reason or 'Customer refund',
        }
        
        signature = self._generate_signature(refund_data)
        refund_data['signature'] = signature
        
        try:
            response = await self._make_cbe_request('/v1/payment/refund', refund_data)
            
            if response.get('status') != 'success':
                raise PaymentProcessingError(
                    f"CBE refund failed: {response.get('message', 'Unknown error')}"
                )
            
            return {
                'refund_id': response.get('refund', {}).get('reference'),
                'status': 'pending',
                'provider_response': response,
            }
            
        except Exception as e:
            raise PaymentProcessingError(f"CBE refund error: {e}")
    
    def verify_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify CBE webhook signature.
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
        Get payment status from CBE.
        """
        return {
            'reference': provider_transaction_id,
            'status': 'unknown',
            'checked_at': datetime.utcnow().isoformat(),
        }
    
    def _generate_bank_reference(self, payment_intent_id: int) -> str:
        """Generate unique bank transfer reference."""
        timestamp = int(datetime.utcnow().timestamp())
        return f"CBE{payment_intent_id}{timestamp}"
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        Generate CBE signature.
        """
        # Sort data for consistent signature
        sorted_data = sorted(data.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_data if k != 'signature'])
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _verify_webhook_signature(self, payload: Dict[str, Any]) -> bool:
        """
        Verify CBE webhook signature.
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
    
    async def _make_cbe_request(
        self, 
        endpoint: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to CBE API.
        """
        import httpx
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'MusicPlatform/1.0',
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "cbe_bank"
    
    def get_supported_currencies(self) -> list[str]:
        """Get supported currencies."""
        return ['ETB']
    
    def get_minimum_amount(self) -> Decimal:
        """Get minimum amount."""
        return Decimal('10.00')  # 10 ETB minimum for bank transfers
    
    def get_maximum_amount(self) -> Decimal:
        """Get maximum amount."""
        return Decimal('1000000.00')  # 1,000,000 ETB maximum
