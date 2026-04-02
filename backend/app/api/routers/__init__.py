"""API routers."""

from .admin_holidays import router as admin_holidays_router
from .calendar import router as calendar_router
from .core import router as core_router
from .marketplace import router as marketplace_router
from .payments import router as payments_router
from .recommendations import router as recommendations_router

try:
    from .audio_analysis import router as audio_analysis_router
except RuntimeError:
    audio_analysis_router = None

__all__ = [
    "admin_holidays_router",
    "audio_analysis_router",
    "calendar_router",
    "core_router",
    "marketplace_router",
    "payments_router",
    "recommendations_router",
]
