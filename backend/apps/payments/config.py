"""
Payment domain configuration.

This module configures payment providers, services, and other
payment domain components.
"""

from typing import Dict, Any

from app.core.settings import get_settings
from apps.payments.providers.base import BasePaymentProvider
from apps.payments.providers.telebirr import TelebirrProvider
from apps.payments.providers.chapa import ChapaProvider
from apps.payments.providers.cbe_bank import CBEBankProvider
from apps.payments.providers.manual_bank import ManualBankProvider
from shared.logging import get_logger

logger = get_logger(__name__)


class PaymentConfig:
    """
    Payment domain configuration.
    
    This class manages payment provider configurations and
    provides factory methods for creating provider instances.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._provider_configs = self._load_provider_configs()
    
    def _load_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load provider configurations from settings."""
        configs = {}
        
        # Telebirr configuration
        if self.settings.telebirr_enabled:
            configs["telebirr"] = {
                "base_url": self.settings.telebirr_base_url or "https://api.telebirr.et",
                "app_id": self.settings.telebirr_app_id,
                "app_secret": self.settings.telebirr_app_secret,
                "merchant_code": self.settings.telebirr_merchant_code,
                "short_code": self.settings.telebirr_short_code,
                "test_mode": self.settings.telebirr_test_mode,
            }
        
        # Chapa configuration
        if self.settings.chapa_enabled:
            configs["chapa"] = {
                "base_url": self.settings.chapa_base_url or "https://api.chapa.co",
                "secret_key": self.settings.chapa_secret_key,
                "webhook_secret": self.settings.chapa_webhook_secret,
                "merchant_id": self.settings.chapa_merchant_id,
                "test_mode": self.settings.chapa_test_mode,
            }
        
        # CBE Bank configuration
        if self.settings.cbe_bank_enabled:
            configs["cbe_bank"] = {
                "base_url": self.settings.cbe_bank_base_url or "https://api.cbe.com.et",
                "api_key": self.settings.cbe_bank_api_key,
                "api_secret": self.settings.cbe_bank_api_secret,
                "account_number": self.settings.cbe_bank_account_number,
                "account_name": self.settings.cbe_bank_account_name,
                "branch_name": self.settings.cbe_bank_branch_name,
                "api_enabled": self.settings.cbe_bank_api_enabled,
                "manual_verification": self.settings.cbe_bank_manual_verification,
                "payment_deadline_hours": self.settings.cbe_bank_payment_deadline_hours,
                "requires_receipt_upload": self.settings.cbe_bank_requires_receipt_upload,
                "auto_approve_threshold": self.settings.cbe_bank_auto_approve_threshold,
            }
        
        # Manual bank configuration
        configs["manual_bank"] = {
            "bank_name": self.settings.manual_bank_name or "Bank",
            "account_number": self.settings.manual_bank_account_number,
            "account_name": self.settings.manual_bank_account_name,
            "branch_name": self.settings.manual_bank_branch_name,
            "payment_deadline_hours": self.settings.manual_bank_payment_deadline_hours or 24,
            "requires_receipt_upload": self.settings.manual_bank_requires_receipt_upload or True,
            "auto_approve_threshold": self.settings.manual_bank_auto_approve_threshold or 0,
        }
        
        return configs
    
    def create_provider(self, provider_name: str) -> BasePaymentProvider:
        """
        Create a payment provider instance.
        
        Args:
            provider_name: Name of the provider to create
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider is not supported or not configured
        """
        if provider_name not in self._provider_configs:
            raise ValueError(f"Provider {provider_name} is not configured")
        
        config = self._provider_configs[provider_name]
        
        # Create provider based on name
        if provider_name == "telebirr":
            return TelebirrProvider(config)
        elif provider_name == "chapa":
            return ChapaProvider(config)
        elif provider_name == "cbe_bank":
            return CBEBankProvider(config)
        elif provider_name == "manual_bank":
            return ManualBankProvider(config)
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider names."""
        return list(self._provider_configs.keys())
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled."""
        return provider_name in self._provider_configs
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get provider configuration."""
        return self._provider_configs.get(provider_name, {})
    
    def validate_provider_configs(self) -> Dict[str, bool]:
        """Validate all provider configurations."""
        validation_results = {}
        
        for provider_name in self._provider_configs:
            try:
                provider = self.create_provider(provider_name)
                provider.validate_config()
                validation_results[provider_name] = True
                logger.info(f"Provider {provider_name} configuration is valid")
            except Exception as e:
                validation_results[provider_name] = False
                logger.error(f"Provider {provider_name} configuration is invalid: {e}")
        
        return validation_results


# Global payment configuration instance
payment_config = PaymentConfig()


def get_payment_config() -> PaymentConfig:
    """Get the global payment configuration instance."""
    return payment_config


def initialize_payment_providers() -> Dict[str, BasePaymentProvider]:
    """
    Initialize all configured payment providers.
    
    Returns:
        Dictionary of provider instances
    """
    providers = {}
    
    for provider_name in payment_config.get_available_providers():
        try:
            provider = payment_config.create_provider(provider_name)
            providers[provider_name] = provider
            logger.info(f"Initialized payment provider: {provider_name}")
        except Exception as e:
            logger.error(f"Failed to initialize provider {provider_name}: {e}")
    
    return providers


# Settings extensions for payment configuration
class PaymentSettings:
    """Payment-specific settings."""
    
    def __init__(self):
        self.settings = get_settings()
    
    # Telebirr settings
    @property
    def telebirr_enabled(self) -> bool:
        return getattr(self.settings, 'telebirr_enabled', False)
    
    @property
    def telebirr_base_url(self) -> str:
        return getattr(self.settings, 'telebirr_base_url', None)
    
    @property
    def telebirr_app_id(self) -> str:
        return getattr(self.settings, 'telebirr_app_id', '')
    
    @property
    def telebirr_app_secret(self) -> str:
        return getattr(self.settings, 'telebirr_app_secret', '')
    
    @property
    def telebirr_merchant_code(self) -> str:
        return getattr(self.settings, 'telebirr_merchant_code', '')
    
    @property
    def telebirr_short_code(self) -> str:
        return getattr(self.settings, 'telebirr_short_code', '')
    
    @property
    def telebirr_test_mode(self) -> bool:
        return getattr(self.settings, 'telebirr_test_mode', True)
    
    # Chapa settings
    @property
    def chapa_enabled(self) -> bool:
        return getattr(self.settings, 'chapa_enabled', False)
    
    @property
    def chapa_base_url(self) -> str:
        return getattr(self.settings, 'chapa_base_url', None)
    
    @property
    def chapa_secret_key(self) -> str:
        return getattr(self.settings, 'chapa_secret_key', '')
    
    @property
    def chapa_webhook_secret(self) -> str:
        return getattr(self.settings, 'chapa_webhook_secret', '')
    
    @property
    def chapa_merchant_id(self) -> str:
        return getattr(self.settings, 'chapa_merchant_id', '')
    
    @property
    def chapa_test_mode(self) -> bool:
        return getattr(self.settings, 'chapa_test_mode', True)
    
    # CBE Bank settings
    @property
    def cbe_bank_enabled(self) -> bool:
        return getattr(self.settings, 'cbe_bank_enabled', False)
    
    @property
    def cbe_bank_base_url(self) -> str:
        return getattr(self.settings, 'cbe_bank_base_url', None)
    
    @property
    def cbe_bank_api_key(self) -> str:
        return getattr(self.settings, 'cbe_bank_api_key', '')
    
    @property
    def cbe_bank_api_secret(self) -> str:
        return getattr(self.settings, 'cbe_bank_api_secret', '')
    
    @property
    def cbe_bank_account_number(self) -> str:
        return getattr(self.settings, 'cbe_bank_account_number', '')
    
    @property
    def cbe_bank_account_name(self) -> str:
        return getattr(self.settings, 'cbe_bank_account_name', '')
    
    @property
    def cbe_bank_branch_name(self) -> str:
        return getattr(self.settings, 'cbe_bank_branch_name', '')
    
    @property
    def cbe_bank_api_enabled(self) -> bool:
        return getattr(self.settings, 'cbe_bank_api_enabled', False)
    
    @property
    def cbe_bank_manual_verification(self) -> bool:
        return getattr(self.settings, 'cbe_bank_manual_verification', True)
    
    @property
    def cbe_bank_payment_deadline_hours(self) -> int:
        return getattr(self.settings, 'cbe_bank_payment_deadline_hours', 24)
    
    @property
    def cbe_bank_requires_receipt_upload(self) -> bool:
        return getattr(self.settings, 'cbe_bank_requires_receipt_upload', True)
    
    @property
    def cbe_bank_auto_approve_threshold(self) -> float:
        return getattr(self.settings, 'cbe_bank_auto_approve_threshold', 0)
    
    # Manual bank settings
    @property
    def manual_bank_name(self) -> str:
        return getattr(self.settings, 'manual_bank_name', 'Bank')
    
    @property
    def manual_bank_account_number(self) -> str:
        return getattr(self.settings, 'manual_bank_account_number', '')
    
    @property
    def manual_bank_account_name(self) -> str:
        return getattr(self.settings, 'manual_bank_account_name', '')
    
    @property
    def manual_bank_branch_name(self) -> str:
        return getattr(self.settings, 'manual_bank_branch_name', '')
    
    @property
    def manual_bank_payment_deadline_hours(self) -> int:
        return getattr(self.settings, 'manual_bank_payment_deadline_hours', 24)
    
    @property
    def manual_bank_requires_receipt_upload(self) -> bool:
        return getattr(self.settings, 'manual_bank_requires_receipt_upload', True)
    
    @property
    def manual_bank_auto_approve_threshold(self) -> float:
        return getattr(self.settings, 'manual_bank_auto_approve_threshold', 0)


# Extend the main settings class with payment settings
def extend_settings_with_payment():
    """Extend the main settings class with payment-specific settings."""
    from app.core.settings import AppSettings
    
    # Add payment settings to AppSettings
    payment_settings = PaymentSettings()
    
    for attr_name in dir(payment_settings):
        if not attr_name.startswith('_'):
            setattr(AppSettings, attr_name, getattr(payment_settings, attr_name))


# Initialize payment settings on import
extend_settings_with_payment()
