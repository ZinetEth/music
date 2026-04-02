"""
Manual bank payment provider for verification workflows.

This provider handles manual payment verification processes
for bank transfers and other offline payment methods.
"""

from datetime import datetime, timedelta
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


class ManualBankProvider(BasePaymentProvider):
    """
    Manual bank payment provider implementation.
    
    Handles payment verification through admin approval processes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bank_name = config.get('bank_name', 'Bank')
        self.account_number = config.get('account_number')
        self.account_name = config.get('account_name')
        self.branch_name = config.get('branch_name', '')
        self.payment_deadline_hours = config.get('payment_deadline_hours', 24)
        self.requires_receipt_upload = config.get('requires_receipt_upload', True)
        self.auto_approve_threshold = config.get('auto_approve_threshold', 0)  # Amount below which auto-approval might be allowed
    
    def validate_config(self) -> None:
        """Validate manual bank configuration."""
        required_fields = ['bank_name', 'account_number', 'account_name']
        
        for field in required_fields:
            if not self.config.get(field):
                raise ProviderConfigurationError(f"Manual bank requires {field} in configuration")
    
    async def initialize_payment(
        self, 
        request: PaymentProcessRequest
    ) -> PaymentProcessResponse:
        """
        Initialize manual bank payment.
        
        Generates payment instructions and reference for manual verification.
        """
        # Validate amount and currency
        self.validate_amount(request.payment_intent.amount)
        self.validate_currency(request.payment_intent.currency)
        
        # Generate unique reference
        reference = self._generate_reference(request.payment_intent.id)
        
        # Create payment instructions
        payment_instructions = {
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_name': self.account_name,
            'branch_name': self.branch_name,
            'amount': float(request.payment_intent.amount),
            'currency': request.payment_intent.currency,
            'reference': reference,
            'description': request.payment_intent.description or 'Payment',
            'payment_deadline': (datetime.utcnow() + timedelta(hours=self.payment_deadline_hours)).isoformat(),
            'requires_receipt_upload': self.requires_receipt_upload,
            'verification_method': 'manual_admin_approval',
        }
        
        # Add additional instructions based on configuration
        if self.requires_receipt_upload:
            payment_instructions['upload_instructions'] = (
                "Please upload a clear photo or screenshot of your payment receipt "
                "including the transaction reference number and amount paid."
            )
        
        # Check if auto-approval might be possible
        can_auto_approve = (
            self.auto_approve_threshold > 0 and 
            request.payment_intent.amount <= self.auto_approve_threshold
        )
        
        return PaymentProcessResponse(
            payment_intent=request.payment_intent,
            transaction={
                'reference': reference,
                'payment_instructions': payment_instructions,
                'verification_method': 'manual',
                'can_auto_approve': can_auto_approve,
                'deadline_hours': self.payment_deadline_hours,
            },
            provider_response={
                'status': 'pending_manual_verification',
                'reference': reference,
                'deadline': payment_instructions['payment_deadline'],
            },
            next_action='manual_payment_required',
            redirect_url=None
        )
    
    async def verify_payment(
        self, 
        request: PaymentVerifyRequest
    ) -> PaymentVerifyResponse:
        """
        Verify manual bank payment status.
        
        Checks if payment has been manually verified by admin.
        """
        # In a real implementation, this would check:
        # 1. Database for admin verification status
        # 2. Receipt upload verification
        # 3. Bank statement matching (if available)
        
        # For now, return pending status indicating manual verification is needed
        return PaymentVerifyResponse(
            payment_intent=request.payment_intent,
            transaction={'reference': request.provider_transaction_id},
            is_verified=False,
            verification_details={
                'status': 'pending_manual_verification',
                'message': 'Payment requires manual verification by admin',
                'verification_method': 'manual',
                'next_steps': [
                    'Upload payment receipt if required',
                    'Wait for admin verification',
                    'Check email for verification status',
                ]
            }
        )
    
    async def process_webhook(
        self, 
        webhook_data: WebhookEventCreate
    ) -> Dict[str, Any]:
        """
        Process webhook for manual bank provider.
        
        Manual provider doesn't receive webhooks from banks,
        but might receive admin verification updates.
        """
        payload = webhook_data.raw_payload
        
        # Verify this is an admin verification webhook
        if payload.get('source') != 'admin_verification':
            raise WebhookVerificationError("Invalid webhook source for manual bank provider")
        
        # Extract verification information
        reference = payload.get('reference')
        verification_status = payload.get('verification_status')
        verified_by = payload.get('verified_by')
        verification_notes = payload.get('notes', '')
        
        if not reference or not verification_status:
            raise WebhookVerificationError("Missing required verification webhook fields")
        
        # Map verification status to payment status
        status_mapping = {
            'approved': 'completed',
            'rejected': 'failed',
            'pending': 'pending',
        }
        
        mapped_status = status_mapping.get(verification_status, 'pending')
        
        return {
            'provider_transaction_id': reference,
            'status': mapped_status,
            'amount': None,  # Would be extracted from original payment
            'processed_at': datetime.utcnow().isoformat(),
            'webhook_data': payload,
            'verification_details': {
                'verified_by': verified_by,
                'verification_notes': verification_notes,
                'verification_method': 'manual_admin_approval',
            }
        }
    
    async def refund_payment(
        self, 
        refund_request: RefundCreate
    ) -> Dict[str, Any]:
        """
        Process manual bank refund.
        
        Manual refunds require admin processing and bank transfer initiation.
        """
        refund_reference = self._generate_reference(refund_request.original_transaction_id, prefix='REF')
        
        return {
            'refund_id': refund_reference,
            'status': 'pending_manual_processing',
            'message': 'Refund requires manual processing and bank transfer initiation',
            'refund_instructions': {
                'method': 'manual_bank_transfer',
                'processing_time': '1-3 business days',
                'customer_action': 'No action required - refund will be processed automatically',
                'tracking_reference': refund_reference,
            },
            'estimated_completion': (datetime.utcnow() + timedelta(days=3)).isoformat(),
        }
    
    def verify_webhook_signature(
        self, 
        payload: str, 
        signature: str, 
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify webhook signature for manual bank provider.
        
        Manual provider webhooks are internal (admin verification),
        so signature verification might be different.
        """
        # For internal admin webhooks, we might use a different verification method
        # This could be based on internal API keys or HMAC with admin secret
        
        # For now, return True for internal webhooks
        # In production, implement proper verification
        return True
    
    def get_payment_status(
        self, 
        provider_transaction_id: str
    ) -> Dict[str, Any]:
        """
        Get payment status for manual bank payment.
        """
        return {
            'reference': provider_transaction_id,
            'status': 'pending_manual_verification',
            'checked_at': datetime.utcnow().isoformat(),
            'verification_method': 'manual_admin_approval',
        }
    
    def _generate_reference(
        self, 
        payment_intent_id: int, 
        prefix: str = 'BNK'
    ) -> str:
        """Generate unique bank transfer reference."""
        timestamp = int(datetime.utcnow().timestamp())
        return f"{prefix}{payment_intent_id}{timestamp}"
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "manual_bank"
    
    def get_supported_currencies(self) -> list[str]:
        """Get supported currencies."""
        return ['ETB', 'USD']  # Manual bank typically supports multiple currencies
    
    def get_minimum_amount(self) -> Decimal:
        """Get minimum amount."""
        return Decimal('5.00')  # 5 ETB minimum
    
    def get_maximum_amount(self) -> Decimal:
        """Get maximum amount."""
        return Decimal('10000000.00')  # 10,000,000 ETB maximum (no real limit for manual)
    
    def get_payment_instructions_template(self) -> Dict[str, Any]:
        """
        Get template for payment instructions.
        """
        return {
            'title': f'Bank Transfer Payment Instructions',
            'steps': [
                f'1. Transfer {self.currency} to the account below',
                f'2. Bank: {self.bank_name}',
                f'3. Account Name: {self.account_name}',
                f'4. Account Number: {self.account_number}',
                f'5. Amount: [PAYMENT_AMOUNT]',
                f'6. Reference: [REFERENCE]',
                '7. Keep your payment receipt',
                '8. Upload receipt if required',
            ],
            'important_notes': [
                'Include the exact reference number in your transfer',
                'Payment must be completed within the deadline',
                'Keep your receipt for verification',
                'Contact support if you have issues',
            ]
        }
