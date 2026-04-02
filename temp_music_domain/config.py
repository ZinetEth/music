"""
Music domain configuration.

This module provides configuration management for music domain
including file storage, search, and feature flags.
"""

from typing import Dict, Any

from app.core.settings import get_settings
from shared.logging import get_logger

logger = get_logger(__name__)


class MusicConfig:
    """
    Music domain configuration.
    
    This class manages music-specific settings and
    provides factory methods for music services.
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    # File storage settings
    @property
    def music_storage_path(self) -> str:
        """Path to music file storage."""
        return getattr(self.settings, 'music_storage_path', './music_files')
    
    @property
    def allowed_audio_formats(self) -> list[str]:
        """Allowed audio file formats."""
        return getattr(self.settings, 'allowed_audio_formats', ['mp3', 'flac', 'wav', 'aac'])
    
    @property
    def max_file_size_mb(self) -> int:
        """Maximum file size in MB."""
        return getattr(self.settings, 'max_file_size_mb', 100)
    
    @property
    def max_file_size_bytes(self) -> int:
        """Maximum file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    # Search and recommendation settings
    @property
    def search_enabled(self) -> bool:
        """Whether search functionality is enabled."""
        return getattr(self.settings, 'search_enabled', True)
    
    @property
    def search_index_path(self) -> str:
        """Path to search index storage."""
        return getattr(self.settings, 'search_index_path', './search_index')
    
    @property
    def recommendation_enabled(self) -> bool:
        """Whether recommendation engine is enabled."""
        return getattr(self.settings, 'recommendation_enabled', False)
    
    @property
    def recommendation_model_path(self) -> str:
        """Path to recommendation model."""
        return getattr(self.settings, 'recommendation_model_path', './models/recommendation.pkl')
    
    # Playlist settings
    @property
    def max_playlist_songs(self) -> int:
        """Maximum songs per playlist."""
        return getattr(self.settings, 'max_playlist_songs', 1000)
    
    @property
    def max_playlist_name_length(self) -> int:
        """Maximum playlist name length."""
        return getattr(self.settings, 'max_playlist_name_length', 255)
    
    @property
    def default_playlist_visibility(self) -> str:
        """Default playlist visibility."""
        return getattr(self.settings, 'default_playlist_visibility', 'public')
    
    # Marketplace settings
    @property
    def marketplace_enabled(self) -> bool:
        """Whether marketplace is enabled."""
        return getattr(self.settings, 'marketplace_enabled', True)
    
    @property
    def marketplace_fee_percentage(self) -> float:
        """Marketplace fee percentage."""
        return getattr(self.settings, 'marketplace_fee_percentage', 5.0)
    
    @property
    def max_listing_price(self) -> float:
        """Maximum listing price."""
        return getattr(self.settings, 'max_listing_price', 10000.0)
    
    @property
    def min_listing_price(self) -> float:
        """Minimum listing price."""
        return getattr(self.settings, 'min_listing_price', 1.0)
    
    # Subscription settings
    @property
    def subscriptions_enabled(self) -> bool:
        """Whether subscriptions are enabled."""
        return getattr(self.settings, 'subscriptions_enabled', True)
    
    @property
    def premium_features(self) -> list[str]:
        """List of premium features."""
        return getattr(self.settings, 'premium_features', [
            'unlimited_playlists',
            'high_quality_audio',
            'offline_downloads',
            'no_ads',
            'advanced_search',
            'exclusive_content'
        ])
    
    @property
    def premium_price_monthly(self) -> float:
        """Monthly premium subscription price."""
        return getattr(self.settings, 'premium_price_monthly', 99.0)
    
    @property
    def premium_price_yearly(self) -> float:
        """Yearly premium subscription price."""
        return getattr(self.settings, 'premium_price_yearly', 990.0)
    
    # Artist features
    @property
    def artist_features_enabled(self) -> bool:
        """Whether artist features are enabled."""
        return getattr(self.settings, 'artist_features_enabled', True)
    
    @property
    def artist_verification_enabled(self) -> bool:
        """Whether artist verification is enabled."""
        return getattr(self.settings, 'artist_verification_enabled', False)
    
    @property
    def max_songs_per_artist(self) -> int:
        """Maximum songs per artist (for free tier)."""
        return getattr(self.settings, 'max_songs_per_artist', 100)
    
    # Social features
    @property
    def social_features_enabled(self) -> bool:
        """Whether social features are enabled."""
        return getattr(self.settings, 'social_features_enabled', True)
    
    @property
    def max_follows_per_user(self) -> int:
        """Maximum follows per user."""
        return getattr(self.settings, 'max_follows_per_user', 1000)
    
    @property
    def max_likes_per_user(self) -> int:
        """Maximum likes per user."""
        return getattr(self.settings, 'max_likes_per_user', 10000)
    
    # Analytics settings
    @property
    def analytics_enabled(self) -> bool:
        """Whether analytics are enabled."""
        return getattr(self.settings, 'analytics_enabled', True)
    
    @property
    def analytics_retention_days(self) -> int:
        """Days to retain analytics data."""
        return getattr(self.settings, 'analytics_retention_days', 365)
    
    @property
    def real_time_analytics(self) -> bool:
        """Whether real-time analytics are enabled."""
        return getattr(self.settings, 'real_time_analytics', False)
    
    # Content moderation
    @property
    def content_moderation_enabled(self) -> bool:
        """Whether content moderation is enabled."""
        return getattr(self.settings, 'content_moderation_enabled', True)
    
    @property
    def auto_approval_threshold(self) -> int:
        """Auto-approval threshold for trusted users."""
        return getattr(self.settings, 'auto_approval_threshold', 10)
    
    @property
    def blocked_words_file(self) -> str:
        """Path to blocked words file."""
        return getattr(self.settings, 'blocked_words_file', './config/blocked_words.txt')
    
    # External integrations
    @property
    def navidrome_enabled(self) -> bool:
        """Whether Navidrome integration is enabled."""
        return getattr(self.settings, 'navidrome_enabled', True)
    
    @property
    def navidrome_url(self) -> str:
        """Navidrome server URL."""
        return getattr(self.settings, 'navidrome_url', 'http://localhost:4533')
    
    @property
    def navidrome_api_key(self) -> str:
        """Navidrome API key."""
        return getattr(self.settings, 'navidrome_api_key', '')
    
    # Performance settings
    @property
    def cache_enabled(self) -> bool:
        """Whether caching is enabled."""
        return getattr(self.settings, 'cache_enabled', True)
    
    @property
    def cache_ttl_seconds(self) -> int:
        """Cache TTL in seconds."""
        return getattr(self.settings, 'cache_ttl_seconds', 300)
    
    @property
    def cache_max_size_mb(self) -> int:
        """Maximum cache size in MB."""
        return getattr(self.settings, 'cache_max_size_mb', 100)
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get all feature flags."""
        return {
            'search': self.search_enabled,
            'recommendations': self.recommendation_enabled,
            'marketplace': self.marketplace_enabled,
            'subscriptions': self.subscriptions_enabled,
            'artist_features': self.artist_features_enabled,
            'social_features': self.social_features_enabled,
            'analytics': self.analytics_enabled,
            'content_moderation': self.content_moderation_enabled,
            'navidrome_integration': self.navidrome_enabled,
            'caching': self.cache_enabled,
        }
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate music domain configuration."""
        validation_results = {}
        
        # Validate file storage
        try:
            import os
            os.makedirs(self.music_storage_path, exist_ok=True)
            validation_results['file_storage'] = True
        except Exception as e:
            logger.error(f"File storage validation failed: {e}")
            validation_results['file_storage'] = False
        
        # Validate search index path
        try:
            if self.search_enabled:
                os.makedirs(self.search_index_path, exist_ok=True)
            validation_results['search_index'] = True
        except Exception as e:
            logger.error(f"Search index validation failed: {e}")
            validation_results['search_index'] = False
        
        # Validate numeric values
        validation_results['max_file_size'] = self.max_file_size_mb > 0
        validation_results['max_playlist_songs'] = self.max_playlist_songs > 0
        validation_results['marketplace_fee'] = 0 <= self.marketplace_fee_percentage <= 100
        validation_results['listing_prices'] = self.min_listing_price > 0 and self.max_listing_price > self.min_listing_price
        
        return validation_results
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information."""
        import os
        
        try:
            stat = os.statvfs(self.music_storage_path)
            total_space = stat.f_frsize * stat.f_blocks
            free_space = stat.f_frsize * stat.f_bavail
            used_space = total_space - free_space
            
            return {
                'total_space_bytes': total_space,
                'free_space_bytes': free_space,
                'used_space_bytes': used_space,
                'usage_percentage': (used_space / total_space) * 100 if total_space > 0 else 0,
                'storage_path': self.music_storage_path
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {
                'error': str(e),
                'storage_path': self.music_storage_path
            }
    
    def is_audio_format_allowed(self, format: str) -> bool:
        """Check if audio format is allowed."""
        return format.lower() in [f.lower() for f in self.allowed_audio_formats]
    
    def is_file_size_valid(self, size_bytes: int) -> bool:
        """Check if file size is valid."""
        return 0 < size_bytes <= self.max_file_size_bytes
    
    def calculate_marketplace_fee(self, price: float) -> float:
        """Calculate marketplace fee for given price."""
        return (price * self.marketplace_fee_percentage) / 100
    
    def calculate_net_price(self, price: float) -> float:
        """Calculate net price after marketplace fee."""
        fee = self.calculate_marketplace_fee(price)
        return price - fee
    
    def get_premium_features_list(self) -> Dict[str, str]:
        """Get premium features with descriptions."""
        feature_descriptions = {
            'unlimited_playlists': 'Create unlimited playlists',
            'high_quality_audio': 'Stream high quality audio (320kbps)',
            'offline_downloads': 'Download songs for offline listening',
            'no_ads': 'Listen without advertisements',
            'advanced_search': 'Advanced search filters and sorting',
            'exclusive_content': 'Access to exclusive content and releases'
        }
        
        return {
            feature: feature_descriptions.get(feature, feature)
            for feature in self.premium_features
            if feature in feature_descriptions
        }


# Global music configuration instance
music_config = MusicConfig()


def get_music_config() -> MusicConfig:
    """Get global music configuration instance."""
    return music_config


def initialize_music_services() -> Dict[str, Any]:
    """
    Initialize music domain services.
    
    Returns:
        Dictionary of initialized services and configuration
    """
    from temp_music_domain.services import SongService, PlaylistService, MarketplaceService, SubscriptionService
    
    # Validate configuration
    validation_results = music_config.validate_configuration()
    
    if not all(validation_results.values()):
        logger.warning("Music domain configuration validation failed", validation_results)
    
    # Initialize services
    services = {
        'song_service': SongService,
        'playlist_service': PlaylistService,
        'marketplace_service': MarketplaceService,
        'subscription_service': SubscriptionService,
        'config': music_config,
        'validation_results': validation_results,
        'feature_flags': music_config.get_feature_flags(),
    }
    
    logger.info(
        "Music domain services initialized",
        services=list(services.keys()),
        feature_flags=services['feature_flags']
    )
    
    return services


# Configuration validation functions
def validate_audio_file(file_path: str) -> Dict[str, Any]:
    """
    Validate audio file.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Validation result with metadata
    """
    import os
    import mimetypes
    
    config = get_music_config()
    
    try:
        # Check file exists
        if not os.path.exists(file_path):
            return {
                'valid': False,
                'error': 'file_not_found',
                'message': 'Audio file not found'
            }
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if not config.is_file_size_valid(file_size):
            return {
                'valid': False,
                'error': 'file_too_large',
                'message': f'File size exceeds maximum of {config.max_file_size_mb}MB',
                'file_size_bytes': file_size,
                'max_size_bytes': config.max_file_size_bytes
            }
        
        # Check file format
        file_ext = os.path.splitext(file_path)[1][1:].lower()
        if not config.is_audio_format_allowed(file_ext):
            return {
                'valid': False,
                'error': 'invalid_format',
                'message': f'File format {file_ext} is not allowed',
                'allowed_formats': config.allowed_audio_formats
            }
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return {
            'valid': True,
            'file_path': file_path,
            'file_size_bytes': file_size,
            'file_format': file_ext,
            'mime_type': mime_type,
            'metadata': {}
        }
        
    except Exception as e:
        logger.error(f"Audio file validation failed: {e}")
        return {
            'valid': False,
            'error': 'validation_error',
            'message': str(e)
        }


def get_audio_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from audio file.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Audio metadata
    """
    try:
        # This would use a library like mutagen or tinytag
        # For now, return basic metadata
        import os
        
        stat = os.stat(file_path)
        
        return {
            'file_path': file_path,
            'file_size_bytes': stat.st_size,
            'modified_at': stat.st_mtime,
            'format': os.path.splitext(file_path)[1][1:].lower(),
            # Would extract actual audio metadata here
            'duration_seconds': None,
            'bitrate': None,
            'sample_rate': None,
            'channels': None,
        }
        
    except Exception as e:
        logger.error(f"Failed to extract audio metadata: {e}")
        return {
            'error': str(e),
            'file_path': file_path
        }
