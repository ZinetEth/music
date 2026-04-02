"""
Payment domain models - completely isolated from business logic.

These models are generic and reusable across any application.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Numeric as SQLAlchemyDecimal,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from shared.db import Base


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)


class PaymentStatus(str, Enum):
    """Payment status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(str, Enum):
    """Payment method enum."""
    TELEBIRR = "telebirr"
    CHAPA = "chapa"
    CBE_BANK = "cbe_bank"
    CBE_BIRR = "cbe_birr"
    STRIPE = "stripe"
    MANUAL_BANK = "manual_bank"
    WALLET = "wallet"
    CASH = "cash"


class TransactionType(str, Enum):
    """Transaction type enum."""
    PAYMENT = "payment"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    PAYOUT = "payout"
    WALLET_TOPUP = "wallet_topup"
    WALLET_WITHDRAWAL = "wallet_withdrawal"


class WebhookStatus(str, Enum):
    """Webhook processing status."""
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRYING = "retrying"


class PaymentIntent(Base):
    """
    Payment intent represents a payment request that can be fulfilled.
    
    This is completely generic - no coupling to specific business objects.
    """
    __tablename__ = "payment_intents"

    id = Column(Integer, primary_key=True, index=True)
    # Generic reference to any object in any app
    app_name = Column(String(50), nullable=False, index=True)
    object_type = Column(String(50), nullable=False, index=True)
    object_id = Column(String(255), nullable=False, index=True)
    
    # Payment details
    amount = Column(SQLAlchemyDecimal(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="ETB")
    description = Column(Text, nullable=True)
    
    # Customer and merchant
    customer_id = Column(String(255), nullable=False, index=True)
    merchant_id = Column(String(255), nullable=True, index=True)
    
    # Status and metadata
    status = Column(String(20), nullable=False, default=PaymentStatus.PENDING.value)
    payment_metadata = Column(JSON, nullable=True, default=dict)
    
    # Provider information
    preferred_provider = Column(String(50), nullable=True)
    provider_transaction_id = Column(String(255), nullable=True, index=True)
    
    # Callback URLs
    success_url = Column(Text, nullable=True)
    cancel_url = Column(Text, nullable=True)
    webhook_url = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    transactions = relationship("PaymentTransaction", back_populates="payment_intent")
    webhooks = relationship("WebhookEvent", back_populates="payment_intent")

    # Constraints
    __table_args__ = (
        UniqueConstraint('app_name', 'object_type', 'object_id', name='unique_payment_intent'),
    )


class PaymentTransaction(Base):
    """
    Individual payment transaction attempts.
    
    Each payment intent can have multiple transactions (retries, different providers).
    """
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    payment_intent_id = Column(Integer, ForeignKey("payment_intents.id"), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(String(20), nullable=False, default=TransactionType.PAYMENT.value)
    amount = Column(SQLAlchemyDecimal(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="ETB")
    
    # Provider information
    provider = Column(String(50), nullable=False, index=True)
    provider_transaction_id = Column(String(255), nullable=True, index=True)
    provider_response = Column(JSON, nullable=True, default=dict)
    
    # Status
    status = Column(String(20), nullable=False, default=PaymentStatus.PENDING.value)
    failure_reason = Column(Text, nullable=True)
    
    # Fees and splits
    provider_fee = Column(SQLAlchemyDecimal(10, 2), nullable=False, default=0)
    platform_fee = Column(SQLAlchemyDecimal(10, 2), nullable=False, default=0)
    net_amount = Column(SQLAlchemyDecimal(10, 2), nullable=False)
    
    # Metadata
    transaction_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    payment_intent = relationship("PaymentIntent", back_populates="transactions")
    refunds = relationship("Refund", back_populates="original_transaction")


class Refund(Base):
    """
    Refund transactions linked to original payments.
    """
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    original_transaction_id = Column(Integer, ForeignKey("payment_transactions.id"), nullable=False, index=True)
    
    # Refund details
    amount = Column(SQLAlchemyDecimal(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="ETB")
    reason = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default=PaymentStatus.PENDING.value)
    provider_refund_id = Column(String(255), nullable=True, index=True)
    provider_response = Column(JSON, nullable=True, default=dict)
    failure_reason = Column(Text, nullable=True)
    
    # Metadata
    transaction_metadata = Column(JSON, nullable=True, default=dict)
    refunded_by = Column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    original_transaction = relationship("PaymentTransaction", back_populates="refunds")


class WebhookEvent(Base):
    """
    Webhook events from payment providers.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    payment_intent_id = Column(Integer, ForeignKey("payment_intents.id"), nullable=True, index=True)
    
    # Event details
    provider = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(String(255), nullable=False, index=True)
    
    # Event data
    raw_payload = Column(JSON, nullable=False)
    processed_payload = Column(JSON, nullable=True, default=dict)
    
    # Processing status
    status = Column(String(20), nullable=False, default=WebhookStatus.PENDING.value)
    processing_attempts = Column(Integer, nullable=False, default=0)
    failure_reason = Column(Text, nullable=True)
    
    # Verification
    signature_verified = Column(Boolean, nullable=False, default=False)
    signature_verification_result = Column(Text, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    payment_intent = relationship("PaymentIntent", back_populates="webhooks")

    # Constraints
    __table_args__ = (
        UniqueConstraint('provider', 'event_id', name='unique_webhook_event'),
    )


class ProviderAccount(Base):
    """
    Payment provider account configurations.
    """
    __tablename__ = "provider_accounts"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)
    account_id = Column(String(255), nullable=False, index=True)
    
    # Account details
    account_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_test = Column(Boolean, nullable=False, default=False)
    
    # Configuration (encrypted)
    config = Column(JSON, nullable=True, default=dict)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Constraints
    __table_args__ = (
        UniqueConstraint('provider', 'account_id', name='unique_provider_account'),
    )


class Payout(Base):
    """
    Payout requests to merchants/providers.
    """
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Payout details
    recipient_id = Column(String(255), nullable=False, index=True)
    recipient_type = Column(String(50), nullable=False, index=True)  # merchant, provider, artist
    amount = Column(SQLAlchemyDecimal(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="ETB")
    
    # Provider and method
    provider = Column(String(50), nullable=False, index=True)
    provider_payout_id = Column(String(255), nullable=True, index=True)
    
    # Status
    status = Column(String(20), nullable=False, default=PaymentStatus.PENDING.value)
    failure_reason = Column(Text, nullable=True)
    
    # Verification
    requires_manual_approval = Column(Boolean, nullable=False, default=False)
    approved_by = Column(String(255), nullable=True, index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    transaction_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class LedgerEntry(Base):
    """
    Financial ledger entries for accounting and reconciliation.
    """
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Entry details
    entry_type = Column(String(50), nullable=False, index=True)  # debit, credit
    account_type = Column(String(50), nullable=False, index=True)  # customer, merchant, platform
    account_id = Column(String(255), nullable=False, index=True)
    
    # Amount
    amount = Column(SQLAlchemyDecimal(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="ETB")
    
    # Reference
    reference_type = Column(String(50), nullable=False, index=True)  # payment, refund, payout
    reference_id = Column(String(255), nullable=False, index=True)
    
    # Description and metadata
    description = Column(Text, nullable=True)
    account_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('reference_type', 'reference_id', 'account_type', 'account_id', name='unique_ledger_entry'),
    )
