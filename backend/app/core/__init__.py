"""Core application configuration."""

from .holidays import DEFAULT_RECOMMENDATIONS, HOLIDAY_RULES
from .recommendation_catalog import SONG_CATALOG

__all__ = ["DEFAULT_RECOMMENDATIONS", "HOLIDAY_RULES", "SONG_CATALOG"]
