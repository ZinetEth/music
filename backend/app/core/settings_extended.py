"""
Extended settings for payment domain.

This extends the base settings with payment-specific configuration
for Ethiopian and international payment providers.
"""

import os
from functools import lru_cache

from app.core.settings import AppSettings, _get_env, _get_bool, _get_int


class PaymentSettings(AppSettings):
    """
    Extended settings class with payment provider configurations.
    
    This extends the base AppSettings to include all the payment
    provider configurations needed for the payment domain.
    """
    
    def __init__(self) -> None:
        super().__init__()
        
        # Payment domain settings
        self.payment_enabled = _get_bool("PAYMENT_ENABLED", True)
        self.payment_default_currency = _get_env("PAYMENT_DEFAULT_CURRENCY", "ETB")
        self.payment_webhook_timeout = _get_int("PAYMENT_WEBHOOK_TIMEOUT", 30)
        self.payment_max_amount = _get_env("PAYMENT_MAX_AMOUNT", "1000000")
        self.payment_min_amount = _get_env("PAYMENT_MIN_AMOUNT", "1")
        
        # Telebirr settings
        self.telebirr_enabled = _get_bool("TELEBIRR_ENABLED", False)
        self.telebirr_base_url = _get_env("TELEBIRR_BASE_URL", "https://api.telebirr.et")
        self.telebirr_app_id = _get_env("TELEBIRR_APP_ID", "")
        self.telebirr_app_secret = _get_env("TELEBIRR_APP_SECRET", "")
        self.telebirr_merchant_code = _get_env("TELEBIRR_MERCHANT_CODE", "")
        self.telebirr_short_code = _get_env("TELEBIRR_SHORT_CODE", "")
        self.telebirr_test_mode = _get_bool("TELEBIRR_TEST_MODE", True)
        
        # Chapa settings
        self.chapa_enabled = _get_bool("CHAPA_ENABLED", False)
        self.chapa_base_url = _get_env("CHAPA_BASE_URL", "https://api.chapa.co")
        self.chapa_secret_key = _get_env("CHAPA_SECRET_KEY", "")
        self.chapa_webhook_secret = _get_env("CHAPA_WEBHOOK_SECRET", "")
        self.chapa_merchant_id = _get_env("CHAPA_MERCHANT_ID", "")
        self.chapa_test_mode = _get_bool("CHAPA_TEST_MODE", True)
        
        # CBE Bank settings
        self.cbe_bank_enabled = _get_bool("CBE_BANK_ENABLED", False)
        self.cbe_bank_base_url = _get_env("CBE_BANK_BASE_URL", "https://api.cbe.com.et")
        self.cbe_bank_api_key = _get_env("CBE_BANK_API_KEY", "")
        self.cbe_bank_api_secret = _get_env("CBE_BANK_API_SECRET", "")
        self.cbe_bank_account_number = _get_env("CBE_BANK_ACCOUNT_NUMBER", "")
        self.cbe_bank_account_name = _get_env("CBE_BANK_ACCOUNT_NAME", "")
        self.cbe_bank_branch_name = _get_env("CBE_BANK_BRANCH_NAME", "")
        self.cbe_bank_api_enabled = _get_bool("CBE_BANK_API_ENABLED", False)
        self.cbe_bank_manual_verification = _get_bool("CBE_BANK_MANUAL_VERIFICATION", True)
        self.cbe_bank_payment_deadline_hours = _get_int("CBE_BANK_PAYMENT_DEADLINE_HOURS", 24)
        self.cbe_bank_requires_receipt_upload = _get_bool("CBE_BANK_REQUIRES_RECEIPT_UPLOAD", True)
        self.cbe_bank_auto_approve_threshold = _get_env("CBE_BANK_AUTO_APPROVE_THRESHOLD", "0")
        
        # Manual bank settings
        self.manual_bank_enabled = _get_bool("MANUAL_BANK_ENABLED", True)
        self.manual_bank_name = _get_env("MANUAL_BANK_NAME", "Bank")
        self.manual_bank_account_number = _get_env("MANUAL_BANK_ACCOUNT_NUMBER", "")
        self.manual_bank_account_name = _get_env("MANUAL_BANK_ACCOUNT_NAME", "")
        self.manual_bank_branch_name = _get_env("MANUAL_BANK_BRANCH_NAME", "")
        self.manual_bank_payment_deadline_hours = _get_int("MANUAL_BANK_PAYMENT_DEADLINE_HOURS", 24)
        self.manual_bank_requires_receipt_upload = _get_bool("MANUAL_BANK_REQUIRES_RECEIPT_UPLOAD", True)
        self.manual_bank_auto_approve_threshold = _get_env("MANUAL_BANK_AUTO_APPROVE_THRESHOLD", "0")
        
        # Payment security settings
        self.payment_idempotency_ttl = _get_int("PAYMENT_IDEMPOTENCY_TTL", 3600)  # 1 hour
        self.payment_webhook_signature_ttl = _get_int("PAYMENT_WEBHOOK_SIGNATURE_TTL", 300)  # 5 minutes
        self.payment_max_retry_attempts = _get_int("PAYMENT_MAX_RETRY_ATTEMPTS", 5)
        self.payment_retry_delay_seconds = _get_int("PAYMENT_RETRY_DELAY_SECONDS", 60)
        
        # Validate payment-specific settings
        self._validate_payment_settings()
    
    def _validate_payment_settings(self) -> None:
        """Validate payment-specific settings."""
        
        # Validate currency
        if len(self.payment_default_currency) != 3:
            raise ValueError("PAYMENT_DEFAULT_CURRENCY must be a 3-letter currency code")
        
        # Validate amounts
        try:
            max_amount = float(self.payment_max_amount)
            min_amount = float(self.payment_min_amount)
            if max_amount <= min_amount:
                raise ValueError("PAYMENT_MAX_AMOUNT must be greater than PAYMENT_MIN_AMOUNT")
        except ValueError:
            raise ValueError("PAYMENT_MAX_AMOUNT and PAYMENT_MIN_AMOUNT must be valid numbers")
        
        # Validate Telebirr settings if enabled
        if self.telebirr_enabled:
            required_telebirr = [
                "telebirr_app_id",
                "telebirr_app_secret", 
                "telebirr_merchant_code",
                "telebirr_short_code"
            ]
            for setting in required_telebirr:
                if not getattr(self, setting):
                    raise ValueError(f"TELEBIRR_ENABLED requires {setting.upper()}")
        
        # Validate Chapa settings if enabled
        if self.chapa_enabled:
            required_chapa = [
                "chapa_secret_key",
                "chapa_webhook_secret",
                "chapa_merchant_id"
            ]
            for setting in required_chapa:
                if not getattr(self, setting):
                    raise ValueError(f"CHAPA_ENABLED requires {setting.upper()}")
        
        # Validate CBE Bank settings if enabled
        if self.cbe_bank_enabled:
            required_cbe = [
                "cbe_bank_account_number",
                "cbe_bank_account_name"
            ]
            for setting in required_cbe:
                if not getattr(self, setting):
                    raise ValueError(f"CBE_BANK_ENABLED requires {setting.upper()}")
            
            # If API is enabled, require API credentials
            if self.cbe_bank_api_enabled:
                required_cbe_api = [
                    "cbe_bank_api_key",
                    "cbe_bank_api_secret"
                ]
                for setting in required_cbe_api:
                    if not getattr(self, setting):
                        raise ValueError(f"CBE_BANK_API_ENABLED requires {setting.upper()}")
        
        # Validate manual bank settings if enabled
        if self.manual_bank_enabled:
            required_manual = [
                "manual_bank_account_number",
                "manual_bank_account_name"
            ]
            for setting in required_manual:
                if not getattr(self, setting):
                    raise ValueError(f"MANUAL_BANK_ENABLED requires {setting.upper()}")
    
    def get_enabled_providers(self) -> list[str]:
        """Get list of enabled payment providers."""
        providers = []
        
        if self.telebirr_enabled:
            providers.append("telebirr")
        
        if self.chapa_enabled:
            providers.append("chapa")
        
        if self.cbe_bank_enabled:
            providers.append("cbe_bank")
        
        if self.manual_bank_enabled:
            providers.append("manual_bank")
        
        return providers
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a specific provider is enabled."""
        return getattr(self, f"{provider_name}_enabled", False)
    
    def get_provider_config(self, provider_name: str) -> dict:
        """Get configuration for a specific provider."""
        config = {}
        
        # Get all settings that start with provider name
        provider_prefix = f"{provider_name}_"
        for attr_name in dir(self):
            if attr_name.startswith(provider_prefix) and not attr_name.startswith("_"):
                config[attr_name] = getattr(self, attr_name)
        
        return config


@lru_cache(maxsize=1)
def get_payment_settings() -> PaymentSettings:
    """Get the payment settings instance."""
    return PaymentSettings()


# Override the original settings function
def get_settings() -> PaymentSettings:
    """Get the extended settings instance."""
    return get_payment_settings()
