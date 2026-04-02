# Payment Domain

A completely isolated, reusable payment processing system designed for Ethiopian and international payments.

## Overview

The payment domain provides a generic, secure, and extensible payment system that can be used across multiple applications without any coupling to specific business domains.

## Features

### Core Features
- **Generic Payment Intents**: Pay for any object in any application
- **Multiple Providers**: Support for Telebirr, Chapa, CBE Bank, and manual bank transfers
- **Idempotency Protection**: Prevent duplicate payments
- **Webhook Processing**: Secure webhook handling with signature verification
- **Refund Support**: Complete refund workflow
- **Audit Logging**: Comprehensive audit trails
- **Rate Limiting**: Built-in rate limiting for security
- **Multi-Currency**: Support for ETB, USD, and other currencies

### Ethiopian Payment Providers
- **Telebirr**: Mobile money payments via USSD
- **Chapa**: Payment aggregator with multiple methods
- **CBE Bank**: Bank transfers and digital banking
- **Manual Bank**: Manual verification workflows

### Security Features
- **Webhook Signature Verification**: Prevent spoofed webhooks
- **Amount Validation**: Prevent amount tampering
- **Idempotency Keys**: Prevent duplicate transactions
- **Rate Limiting**: Prevent abuse
- **Audit Trails**: Complete transaction history
- **Secure Configuration**: Encrypted provider credentials

## Architecture

### Domain Structure
```
apps/payments/
├── models.py              # Database models (generic, reusable)
├── schemas.py             # API schemas
├── providers/             # Payment provider implementations
│   ├── base.py           # Base provider interface
│   ├── telebirr.py       # Telebirr provider
│   ├── chapa.py          # Chapa provider
│   ├── cbe_bank.py       # CBE Bank provider
│   └── manual_bank.py    # Manual bank provider
├── services/              # Business logic services
│   ├── payment_service.py # Core payment processing
│   └── webhook_service.py # Webhook processing
├── api/                   # API endpoints
│   └── routers.py        # FastAPI routers
├── config.py              # Configuration management
└── main.py                # Application entry point
```

### Key Concepts

#### PaymentIntent
A generic payment request that can be used for any object:
```python
{
    "app_name": "music_platform",
    "object_type": "playlist",
    "object_id": "playlist_123",
    "amount": 99.99,
    "currency": "ETB",
    "customer_id": "user_456",
    "description": "Premium playlist purchase"
}
```

#### Provider Adapters
All providers implement the same interface:
```python
class BasePaymentProvider:
    async def initialize_payment(request) -> PaymentProcessResponse
    async def verify_payment(request) -> PaymentVerifyResponse
    async def process_webhook(webhook_data) -> Dict[str, Any]
    async def refund_payment(refund_request) -> Dict[str, Any]
    def verify_webhook_signature(payload, signature, headers) -> bool
```

## Quick Start

### 1. Configuration

Add payment provider settings to your `.env` file:

```bash
# Enable payment domain
PAYMENT_ENABLED=true
PAYMENT_DEFAULT_CURRENCY=ETB

# Telebirr configuration
TELEBIRR_ENABLED=true
TELEBIRR_APP_ID=your_app_id
TELEBIRR_APP_SECRET=your_app_secret
TELEBIRR_MERCHANT_CODE=your_merchant_code
TELEBIRR_SHORT_CODE=your_short_code

# Chapa configuration
CHAPA_ENABLED=true
CHAPA_SECRET_KEY=your_secret_key
CHAPA_WEBHOOK_SECRET=your_webhook_secret
CHAPA_MERCHANT_ID=your_merchant_id

# CBE Bank configuration
CBE_BANK_ENABLED=true
CBE_BANK_ACCOUNT_NUMBER=1000000000
CBE_BANK_ACCOUNT_NAME="Your Company Name"
CBE_BANK_BRANCH_NAME="Main Branch"
CBE_BANK_MANUAL_VERIFICATION=true
```

### 2. Database Setup

The payment domain uses SQLAlchemy models. Run migrations to create tables:

```python
from shared.db import create_tables
create_tables()
```

### 3. Basic Usage

```python
from apps.payments.services.payment_service import PaymentService
from apps.payments.schemas import PaymentIntentCreate

# Create payment intent
service = PaymentService(db)
intent = await service.create_payment_intent(
    PaymentIntentCreate(
        app_name="music_platform",
        object_type="playlist",
        object_id="playlist_123",
        amount=99.99,
        currency="ETB",
        customer_id="user_456",
        description="Premium playlist purchase"
    )
)

# Process payment
from apps.payments.schemas import PaymentProcessRequest
process_response = await service.process_payment(
    PaymentProcessRequest(
        payment_intent_id=intent.id,
        provider="telebirr"
    )
)
```

## API Endpoints

### Payment Intents
- `POST /api/v1/payments/intents` - Create payment intent
- `GET /api/v1/payments/intents/{id}` - Get payment intent
- `GET /api/v1/payments/intents` - List payment intents

### Payment Processing
- `POST /api/v1/payments/process` - Process payment
- `POST /api/v1/payments/verify` - Verify payment status

### Refunds
- `POST /api/v1/payments/refunds` - Create refund

### Webhooks
- `POST /api/v1/payments/webhooks/{provider}` - Process webhook

### Admin
- `GET /api/v1/payments/admin/webhooks` - List webhooks (admin)
- `POST /api/v1/payments/admin/webhooks/{id}/retry` - Retry webhook (admin)

## Provider Configuration

### Telebirr
```bash
TELEBIRR_ENABLED=true
TELEBIRR_BASE_URL=https://api.telebirr.et
TELEBIRR_APP_ID=your_app_id
TELEBIRR_APP_SECRET=your_app_secret
TELEBIRR_MERCHANT_CODE=your_merchant_code
TELEBIRR_SHORT_CODE=your_short_code
TELEBIRR_TEST_MODE=true
```

### Chapa
```bash
CHAPA_ENABLED=true
CHAPA_BASE_URL=https://api.chapa.co
CHAPA_SECRET_KEY=your_secret_key
CHAPA_WEBHOOK_SECRET=your_webhook_secret
CHAPA_MERCHANT_ID=your_merchant_id
CHAPA_TEST_MODE=true
```

### CBE Bank
```bash
CBE_BANK_ENABLED=true
CBE_BANK_ACCOUNT_NUMBER=1000000000
CBE_BANK_ACCOUNT_NAME="Your Company Name"
CBE_BANK_BRANCH_NAME="Main Branch"
CBE_BANK_MANUAL_VERIFICATION=true
CBE_BANK_PAYMENT_DEADLINE_HOURS=24
CBE_BANK_REQUIRES_RECEIPT_UPLOAD=true
```

### Manual Bank
```bash
MANUAL_BANK_ENABLED=true
MANUAL_BANK_NAME="Commercial Bank of Ethiopia"
MANUAL_BANK_ACCOUNT_NUMBER=1000000000
MANUAL_BANK_ACCOUNT_NAME="Your Company Name"
MANUAL_BANK_PAYMENT_DEADLINE_HOURS=24
MANUAL_BANK_REQUIRES_RECEIPT_UPLOAD=true
```

## Security Considerations

### Webhook Security
- All webhooks must be signed by the provider
- Signature verification prevents spoofed webhooks
- Webhooks are processed idempotently

### Idempotency
- Use idempotency keys for payment creation
- Prevents duplicate payments from network retries
- Keys are stored with expiration

### Rate Limiting
- API endpoints are rate limited by IP
- Prevents abuse and brute force attacks
- Configurable limits per provider

### Audit Logging
- All payment operations are logged
- Structured JSON logs for easy parsing
- Includes request IDs for tracing

## Error Handling

### Payment Errors
- `PaymentNotFoundError` - Payment intent not found
- `InvalidPaymentStatusError` - Invalid payment status for operation
- `IdempotencyError` - Duplicate idempotency key
- `PaymentProcessingError` - Provider processing error

### Webhook Errors
- `DuplicateWebhookError` - Webhook already processed
- `WebhookVerificationFailedError` - Invalid webhook signature
- `WebhookProcessingError` - Webhook processing failed

## Testing

### Unit Tests
```python
import pytest
from apps.payments.services.payment_service import PaymentService
from apps.payments.schemas import PaymentIntentCreate

def test_create_payment_intent():
    service = PaymentService(db)
    intent = await service.create_payment_intent(
        PaymentIntentCreate(
            app_name="test_app",
            object_type="test_object",
            object_id="test_123",
            amount=10.00,
            currency="ETB",
            customer_id="test_user"
        )
    )
    assert intent.status == "pending"
```

### Provider Tests
```python
from apps.payments.providers.telebirr import TelebirrProvider

def test_telebirr_provider():
    config = {
        "app_id": "test_id",
        "app_secret": "test_secret",
        "merchant_code": "test_merchant",
        "short_code": "test_code"
    }
    provider = TelebirrProvider(config)
    assert provider.get_provider_name() == "telebirr"
```

## Monitoring

### Health Checks
- `/health` - Basic health check
- `/health/ready` - Readiness check with provider validation
- `/health/live` - Liveness check

### Metrics
- Request count and response times
- Provider success rates
- Error rates by provider
- Webhook processing statistics

### Logging
- Structured JSON logs
- Request tracing with request IDs
- Payment operation logging
- Security event logging

## Deployment

### Docker Configuration
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8001

CMD ["uvicorn", "apps.payments.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Environment Variables
See `.env.example` for all available configuration options.

### Database Migration
```python
from shared.db import create_tables
create_tables()
```

## Integration Examples

### Music Platform Integration
```python
# Create payment for playlist purchase
payment_intent = await payment_service.create_payment_intent(
    PaymentIntentCreate(
        app_name="music_platform",
        object_type="playlist",
        object_id=playlist.id,
        amount=playlist.price,
        currency="ETB",
        customer_id=user.id,
        description=f"Purchase playlist: {playlist.name}"
    )
)

# Process payment
process_response = await payment_service.process_payment(
    PaymentProcessRequest(
        payment_intent_id=payment_intent.id,
        provider="telebirr"
    )
)
```

### E-commerce Integration
```python
# Create payment for product purchase
payment_intent = await payment_service.create_payment_intent(
    PaymentIntentCreate(
        app_name="ecommerce",
        object_type="product",
        object_id=product.id,
        amount=product.price,
        currency="ETB",
        customer_id=customer.id,
        description=f"Purchase product: {product.name}"
    )
)
```

### Subscription Integration
```python
# Create payment for subscription
payment_intent = await payment_service.create_payment_intent(
    PaymentIntentCreate(
        app_name="subscription",
        object_type="subscription",
        object_id=subscription.id,
        amount=subscription.monthly_price,
        currency="ETB",
        customer_id=user.id,
        description=f"Monthly subscription: {subscription.name}"
    )
)
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure security best practices
5. Add proper error handling and logging

## License

This payment domain is part of the larger music platform project and follows the same licensing terms.
