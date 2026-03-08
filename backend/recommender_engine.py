from dataclasses import dataclass
from datetime import date, datetime
from math import exp

from routers.calendar import _gregorian_to_ethiopian

# Optional "best practice" model imports. Engine falls back if not installed.
try:
    from lightfm import LightFM  # type: ignore
except Exception:  # pragma: no cover
    LightFM = None

try:
    from implicit.als import AlternatingLeastSquares  # type: ignore
except Exception:  # pragma: no cover
    AlternatingLeastSquares = None


@dataclass
class SongCandidate:
    navidrome_song_id: str
    title: str
    artist: str
    genre: str
    country: str
    language: str
    release_date: str
    play_count_7d: int
    like_count_7d: int
    skip_rate: float
    playlist_id: str | None = None


class PopularityModel:
    def score(self, song: SongCandidate) -> float:
        # Weighted engagement score with skip penalty.
        return (
            (song.play_count_7d * 0.6)
            + (song.like_count_7d * 1.8)
            - (song.skip_rate * 20.0)
        )


class RecencyModel:
    def score(self, song: SongCandidate, target_date: date) -> float:
        released = datetime.strptime(song.release_date, "%Y-%m-%d").date()
        age_days = max((target_date - released).days, 0)
        # Exponential decay: fresh songs rank higher.
        return exp(-age_days / 45.0) * 100.0


class LocationModel:
    def score(self, song: SongCandidate, location: str | None) -> float:
        if not location:
            return 0.0
        loc = location.strip().lower()
        country = song.country.strip().lower()
        return 35.0 if loc == country else 0.0


class HolidayContextModel:
    def __init__(self, holiday_rules: list[dict]):
        self.holiday_rules = holiday_rules

    def detect_holiday_key(self, target_date: date) -> str | None:
        _eth_year, eth_month, eth_day = _gregorian_to_ethiopian(
            target_date.year, target_date.month, target_date.day
        )
        for rule in self.holiday_rules:
            if rule["eth_month"] == eth_month and rule["eth_day"] == eth_day:
                return rule["key"]
        return None

    def score(self, song: SongCandidate, holiday_key: str | None) -> float:
        if not holiday_key:
            return 0.0
        # Boost songs tied to holiday playlists by song/playlist id convention.
        # This stays deterministic while you wire real mapping tables later.
        if holiday_key in song.navidrome_song_id.lower():
            return 40.0
        if song.playlist_id and holiday_key in song.playlist_id.lower():
            return 40.0
        if song.genre.lower() in {"traditional", "gospel"}:
            return 12.0
        return 6.0


class HybridRecommender:
    def __init__(self, holiday_rules: list[dict]):
        self.popularity = PopularityModel()
        self.recency = RecencyModel()
        self.location = LocationModel()
        self.holiday = HolidayContextModel(holiday_rules)

    def rank(
        self,
        songs: list[SongCandidate],
        target_date: date,
        location: str | None,
        limit: int = 20,
    ) -> tuple[list[dict], str | None, str]:
        holiday_key = self.holiday.detect_holiday_key(target_date)
        backend = "hybrid_heuristic"
        if LightFM is not None or AlternatingLeastSquares is not None:
            backend = "hybrid_with_optional_ml_imports"

        scored: list[dict] = []
        for song in songs:
            popularity_score = self.popularity.score(song)
            recency_score = self.recency.score(song, target_date)
            location_score = self.location.score(song, location)
            holiday_score = self.holiday.score(song, holiday_key)

            final_score = (
                popularity_score * 0.45
                + recency_score * 0.25
                + location_score * 0.15
                + holiday_score * 0.15
            )

            scored.append(
                {
                    "song_id": song.navidrome_song_id,
                    "title": song.title,
                    "artist": song.artist,
                    "genre": song.genre,
                    "score": round(final_score, 4),
                    "score_breakdown": {
                        "popularity": round(popularity_score, 4),
                        "recency": round(recency_score, 4),
                        "location": round(location_score, 4),
                        "holiday_context": round(holiday_score, 4),
                    },
                }
            )

        ranked = sorted(scored, key=lambda s: s["score"], reverse=True)[:limit]
        return ranked, holiday_key, backend
