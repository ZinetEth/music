"""
Payment domain schemas - generic and reusable across applications.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# Enums for API
class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethodEnum(str, Enum):
    TELEBIRR = "telebirr"
    CHAPA = "chapa"
    CBE_BANK = "cbe_bank"
    CBE_BIRR = "cbe_birr"
    STRIPE = "stripe"
    MANUAL_BANK = "manual_bank"
    WALLET = "wallet"
    CASH = "cash"


class TransactionTypeEnum(str, Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    PAYOUT = "payout"
    WALLET_TOPUP = "wallet_topup"
    WALLET_WITHDRAWAL = "wallet_withdrawal"


# Base schemas
class BasePaymentSchema(BaseModel):
    """Base schema for payment operations."""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# Payment Intent schemas
class PaymentIntentCreate(BaseModel):
    """Create a new payment intent."""
    app_name: str = Field(..., min_length=1, max_length=50, description="Application name")
    object_type: str = Field(..., min_length=1, max_length=50, description="Type of object being paid for")
    object_id: str = Field(..., min_length=1, max_length=255, description="ID of the object")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="ETB", max_length=3, description="Currency code")
    description: Optional[str] = Field(None, max_length=500, description="Payment description")
    customer_id: str = Field(..., min_length=1, max_length=255, description="Customer identifier")
    merchant_id: Optional[str] = Field(None, max_length=255, description="Merchant identifier")
    preferred_provider: Optional[PaymentMethodEnum] = Field(None, description="Preferred payment provider")
    success_url: Optional[str] = Field(None, max_length=500, description="Success callback URL")
    cancel_url: Optional[str] = Field(None, max_length=500, description="Cancel callback URL")
    webhook_url: Optional[str] = Field(None, max_length=500, description="Webhook URL")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class PaymentIntentUpdate(BaseModel):
    """Update payment intent."""
    status: Optional[PaymentStatusEnum] = Field(None, description="Payment status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class PaymentIntentResponse(BasePaymentSchema):
    """Payment intent response."""
    id: int
    app_name: str
    object_type: str
    object_id: str
    amount: Decimal
    currency: str
    description: Optional[str]
    customer_id: str
    merchant_id: Optional[str]
    status: PaymentStatusEnum
    metadata: Dict[str, Any]
    preferred_provider: Optional[str]
    provider_transaction_id: Optional[str]
    success_url: Optional[str]
    cancel_url: Optional[str]
    webhook_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    completed_at: Optional[datetime]


# Payment Transaction schemas
class PaymentTransactionCreate(BaseModel):
    """Create a payment transaction."""
    payment_intent_id: int = Field(..., description="Payment intent ID")
    transaction_type: TransactionTypeEnum = Field(default=TransactionTypeEnum.PAYMENT)
    amount: Decimal = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="ETB", max_length=3, description="Currency code")
    provider: PaymentMethodEnum = Field(..., description="Payment provider")
    provider_transaction_id: Optional[str] = Field(None, max_length=255, description="Provider transaction ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PaymentTransactionResponse(BasePaymentSchema):
    """Payment transaction response."""
    id: int
    payment_intent_id: int
    transaction_type: str
    amount: Decimal
    currency: str
    provider: str
    provider_transaction_id: Optional[str]
    provider_response: Dict[str, Any]
    status: PaymentStatusEnum
    failure_reason: Optional[str]
    provider_fee: Decimal
    platform_fee: Decimal
    net_amount: Decimal
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]


# Refund schemas
class RefundCreate(BaseModel):
    """Create a refund."""
    original_transaction_id: int = Field(..., description="Original transaction ID")
    amount: Decimal = Field(..., gt=0, description="Refund amount")
    currency: str = Field(default="ETB", max_length=3, description="Currency code")
    reason: Optional[str] = Field(None, max_length=500, description="Refund reason")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    refunded_by: Optional[str] = Field(None, max_length=255, description="Who initiated the refund")


class RefundResponse(BasePaymentSchema):
    """Refund response."""
    id: int
    original_transaction_id: int
    amount: Decimal
    currency: str
    reason: Optional[str]
    status: PaymentStatusEnum
    provider_refund_id: Optional[str]
    provider_response: Dict[str, Any]
    failure_reason: Optional[str]
    metadata: Dict[str, Any]
    refunded_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]


# Webhook schemas
class WebhookEventCreate(BaseModel):
    """Create a webhook event."""
    provider: str = Field(..., max_length=50, description="Provider name")
    event_type: str = Field(..., max_length=100, description="Event type")
    event_id: str = Field(..., max_length=255, description="Event ID")
    raw_payload: Dict[str, Any] = Field(..., description="Raw webhook payload")
    payment_intent_id: Optional[int] = Field(None, description="Associated payment intent ID")


class WebhookEventResponse(BasePaymentSchema):
    """Webhook event response."""
    id: int
    payment_intent_id: Optional[int]
    provider: str
    event_type: str
    event_id: str
    raw_payload: Dict[str, Any]
    processed_payload: Dict[str, Any]
    status: str
    processing_attempts: int
    failure_reason: Optional[str]
    signature_verified: bool
    signature_verification_result: Optional[str]
    received_at: datetime
    processed_at: Optional[datetime]


# Provider Account schemas
class ProviderAccountCreate(BaseModel):
    """Create a provider account."""
    provider: str = Field(..., max_length=50, description="Provider name")
    account_id: str = Field(..., max_length=255, description="Account ID")
    account_name: str = Field(..., max_length=255, description="Account name")
    is_active: bool = Field(default=True, description="Account active status")
    is_test: bool = Field(default=False, description="Test account flag")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Provider configuration")
    rate_limit_per_minute: int = Field(default=60, gt=0, description="Rate limit per minute")


class ProviderAccountResponse(BasePaymentSchema):
    """Provider account response."""
    id: int
    provider: str
    account_id: str
    account_name: str
    is_active: bool
    is_test: bool
    config: Dict[str, Any]
    rate_limit_per_minute: int
    created_at: datetime
    updated_at: datetime


# Payout schemas
class PayoutCreate(BaseModel):
    """Create a payout."""
    recipient_id: str = Field(..., max_length=255, description="Recipient identifier")
    recipient_type: str = Field(..., max_length=50, description="Recipient type")
    amount: Decimal = Field(..., gt=0, description="Payout amount")
    currency: str = Field(default="ETB", max_length=3, description="Currency code")
    provider: PaymentMethodEnum = Field(..., description="Payment provider")
    requires_manual_approval: bool = Field(default=False, description="Requires manual approval")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PayoutUpdate(BaseModel):
    """Update payout."""
    status: Optional[PaymentStatusEnum] = Field(None, description="Payout status")
    failure_reason: Optional[str] = Field(None, max_length=500, description="Failure reason")
    approved_by: Optional[str] = Field(None, max_length=255, description="Approver ID")


class PayoutResponse(BasePaymentSchema):
    """Payout response."""
    id: int
    recipient_id: str
    recipient_type: str
    amount: Decimal
    currency: str
    provider: str
    provider_payout_id: Optional[str]
    status: PaymentStatusEnum
    failure_reason: Optional[str]
    requires_manual_approval: bool
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime]


# Ledger schemas
class LedgerEntryCreate(BaseModel):
    """Create a ledger entry."""
    entry_type: str = Field(..., pattern="^(debit|credit)$", description="Entry type")
    account_type: str = Field(..., max_length=50, description="Account type")
    account_id: str = Field(..., max_length=255, description="Account ID")
    amount: Decimal = Field(..., description="Amount")
    currency: str = Field(default="ETB", max_length=3, description="Currency code")
    reference_type: str = Field(..., max_length=50, description="Reference type")
    reference_id: str = Field(..., max_length=255, description="Reference ID")
    description: Optional[str] = Field(None, max_length=500, description="Entry description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class LedgerEntryResponse(BasePaymentSchema):
    """Ledger entry response."""
    id: int
    entry_type: str
    account_type: str
    account_id: str
    amount: Decimal
    currency: str
    reference_type: str
    reference_id: str
    description: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


# Payment processing schemas
class PaymentProcessRequest(BaseModel):
    """Process a payment."""
    payment_intent_id: int = Field(..., description="Payment intent ID")
    provider: Optional[PaymentMethodEnum] = Field(None, description="Specific provider to use")
    payment_method_details: Optional[Dict[str, Any]] = Field(None, description="Payment method details")
    idempotency_key: Optional[str] = Field(None, max_length=255, description="Idempotency key")


class PaymentProcessResponse(BaseModel):
    """Payment processing response."""
    payment_intent: PaymentIntentResponse
    transaction: PaymentTransactionResponse
    provider_response: Dict[str, Any]
    next_action: Optional[str] = Field(None, description="Next required action")
    redirect_url: Optional[str] = Field(None, description="Redirect URL if needed")


class PaymentVerifyRequest(BaseModel):
    """Verify a payment."""
    payment_intent_id: int = Field(..., description="Payment intent ID")
    provider: Optional[str] = Field(None, description="Provider name")
    provider_transaction_id: Optional[str] = Field(None, description="Provider transaction ID")
    verification_data: Optional[Dict[str, Any]] = Field(None, description="Verification data")


class PaymentVerifyResponse(BaseModel):
    """Payment verification response."""
    payment_intent: PaymentIntentResponse
    transaction: PaymentTransactionResponse
    is_verified: bool
    verification_details: Dict[str, Any]


# List and filter schemas
class PaymentIntentList(BaseModel):
    """Payment intent list response."""
    items: List[PaymentIntentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class TransactionList(BaseModel):
    """Transaction list response."""
    items: List[PaymentTransactionResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# Error response schemas
class PaymentError(BaseModel):
    """Payment error response."""
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    payment_intent_id: Optional[int] = None
    provider: Optional[str] = None
    retry_possible: bool = False


class ValidationError(BaseModel):
    """Validation error response."""
    field: str
    message: str
    code: str


class APIErrorResponse(BaseModel):
    """General API error response."""
    error: str
    message: str
    error_code: str
    validation_errors: Optional[List[ValidationError]] = None
    timestamp: datetime
    request_id: Optional[str] = None


# Statistics schemas
class PaymentStats(BaseModel):
    """Payment statistics."""
    total_amount: Decimal
    total_count: int
    successful_amount: Decimal
    successful_count: int
    failed_amount: Decimal
    failed_count: int
    pending_amount: Decimal
    pending_count: int
    refunded_amount: Decimal
    refunded_count: int
    period_start: datetime
    period_end: datetime


class ProviderStats(BaseModel):
    """Provider statistics."""
    provider: str
    total_transactions: int
    success_rate: float
    average_processing_time: Optional[float] = None
    total_volume: Decimal
    total_fees: Decimal
    error_rate: float
