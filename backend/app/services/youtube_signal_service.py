from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.settings import get_settings
from app.utils.cache import TTLCache


@dataclass
class YouTubeTrend:
    title: str
    channel_title: str
    region_code: str
    video_id: str
    published_at: str | None
    category_id: str | None
    tags: list[str]


class YouTubeSignalService:
    """Optional YouTube regional trend provider for recommendation boosts."""

    _cache: TTLCache[list[YouTubeTrend]] | None = None

    def __init__(self) -> None:
        self.settings = get_settings()
        if YouTubeSignalService._cache is None:
            YouTubeSignalService._cache = TTLCache(
                ttl_seconds=self.settings.youtube_trends_ttl_seconds
            )

    def is_enabled(self) -> bool:
        return (
            self.settings.youtube_trends_enabled
            and bool(self.settings.youtube_api_key)
        )

    def get_trending_tracks(self, location: str | None) -> list[YouTubeTrend]:
        if not self.is_enabled():
            return []

        region_code = self._resolve_region_code(location)
        cache_key = f"youtube-trends:{region_code}:{self.settings.youtube_trends_max_results}"
        assert YouTubeSignalService._cache is not None
        return YouTubeSignalService._cache.get_or_set(
            cache_key,
            lambda: self._fetch_trends(region_code),
        )

    def _resolve_region_code(self, location: str | None) -> str:
        if not location:
            return self.settings.youtube_region_default.upper()

        normalized = location.strip().lower()
        aliases = {
            "ethiopia": "ET",
            "et": "ET",
            "kenya": "KE",
            "ke": "KE",
            "uganda": "UG",
            "ug": "UG",
            "tanzania": "TZ",
            "tz": "TZ",
            "rwanda": "RW",
            "rw": "RW",
            "united states": "US",
            "usa": "US",
            "us": "US",
            "united kingdom": "GB",
            "uk": "GB",
            "gb": "GB",
        }
        return aliases.get(normalized, self.settings.youtube_region_default.upper())

    def _fetch_trends(self, region_code: str) -> list[YouTubeTrend]:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "chart": "mostPopular",
            "videoCategoryId": "10",
            "regionCode": region_code,
            "maxResults": self.settings.youtube_trends_max_results,
            "key": self.settings.youtube_api_key,
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        trends: list[YouTubeTrend] = []
        for item in payload.get("items", []):
            snippet: dict[str, Any] = item.get("snippet", {})
            trends.append(
                YouTubeTrend(
                    title=snippet.get("title", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    region_code=region_code,
                    video_id=item.get("id", ""),
                    published_at=snippet.get("publishedAt"),
                    category_id=snippet.get("categoryId"),
                    tags=[tag.lower() for tag in snippet.get("tags", []) if isinstance(tag, str)],
                )
            )
        return trends
