from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from math import exp, sqrt
from typing import Any

from app.api.routers.calendar import _gregorian_to_ethiopian


@dataclass
class TasteVector:
    qenet_mode_affinity: dict[str, float]
    genre_affinity: dict[str, float]
    average_tempo: float
    acoustic_signature: dict[str, float]


@dataclass
class SongCandidate:
    navidrome_song_id: str
    title: str
    artist: str
    genre: str
    country: str | None
    language: str | None
    release_date: str | None
    play_count_7d: int
    like_count_7d: int
    skip_rate: float
    playlist_id: str | None = None
    qenet_mode: str | None = None
    tempo: float = 0.0
    extracted_features: dict[str, Any] | None = None


class PopularityModel:
    def score(self, song: SongCandidate) -> float:
        return (
            (song.play_count_7d * 0.6)
            + (song.like_count_7d * 1.8)
            - (song.skip_rate * 20.0)
        )


class RecencyModel:
    def score(self, song: SongCandidate, target_date: datetime.date) -> float:
        if not song.release_date:
            return 0.0
        released = datetime.strptime(song.release_date, "%Y-%m-%d").date()
        age_days = max((target_date - released).days, 0)
        return exp(-age_days / 45.0) * 100.0


class LocationModel:
    def score(self, song: SongCandidate, location: str | None) -> float:
        if not location or not song.country:
            return 0.0
        loc = location.strip().lower()
        country = song.country.strip().lower()
        return 35.0 if loc == country else 0.0


class HolidayContextModel:
    def __init__(self, holiday_rules: list[dict]):
        self.holiday_rules = holiday_rules

    def detect_holiday_key(self, target_date: datetime.date) -> str | None:
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
        target_date: datetime.date,
        location: str | None,
        limit: int = 20,
    ) -> tuple[list[dict], str | None, str]:
        holiday_key = self.holiday.detect_holiday_key(target_date)
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
                    "qenet_mode": song.qenet_mode,
                    "country": song.country,
                    "score": round(final_score, 4),
                    "score_breakdown": {
                        "popularity": round(popularity_score, 4),
                        "recency": round(recency_score, 4),
                        "location": round(location_score, 4),
                        "holiday_context": round(holiday_score, 4),
                    },
                }
            )

        ranked = sorted(scored, key=lambda song: song["score"], reverse=True)[:limit]
        return ranked, holiday_key, "hybrid_heuristic"


class PersonalizedRecommender:
    def cosine_similarity(self, left: TasteVector, right: TasteVector) -> float:
        left_values: dict[str, float] = {}
        right_values: dict[str, float] = {}

        for key, value in left.qenet_mode_affinity.items():
            left_values[f"qenet:{key}"] = value
        for key, value in right.qenet_mode_affinity.items():
            right_values[f"qenet:{key}"] = value

        for key, value in left.genre_affinity.items():
            left_values[f"genre:{key}"] = value
        for key, value in right.genre_affinity.items():
            right_values[f"genre:{key}"] = value

        for key, value in left.acoustic_signature.items():
            left_values[f"acoustic:{key}"] = value
        for key, value in right.acoustic_signature.items():
            right_values[f"acoustic:{key}"] = value

        left_values["tempo"] = left.average_tempo / 220.0 if left.average_tempo else 0.0
        right_values["tempo"] = (
            right.average_tempo / 220.0 if right.average_tempo else 0.0
        )

        keys = set(left_values) | set(right_values)
        dot = sum(
            left_values.get(key, 0.0) * right_values.get(key, 0.0)
            for key in keys
        )
        left_norm = sqrt(sum(value * value for value in left_values.values()))
        right_norm = sqrt(sum(value * value for value in right_values.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _content_affinity(self, song: Any, vector: TasteVector) -> float:
        score = 0.0
        if song.qenet_mode:
            score += vector.qenet_mode_affinity.get(song.qenet_mode, 0.0) * 100
        if song.genre:
            score += vector.genre_affinity.get(song.genre, 0.0) * 80
        if vector.average_tempo and song.tempo:
            tempo_distance = abs(vector.average_tempo - song.tempo)
            score += max(0.0, 30.0 - min(tempo_distance / 2.0, 30.0))

        features = song.extracted_features or {}
        for key, preference in vector.acoustic_signature.items():
            raw = features.get(key)
            if isinstance(raw, int | float):
                score += max(0.0, 20.0 - abs(preference - float(raw)) * 10)
        return score

    def _peer_preference(
        self,
        user_id: int,
        song_id: str,
        songs: list[Any],
        events: list[Any],
        vector: TasteVector,
    ) -> float:
        user_vectors: dict[int, TasteVector] = {}
        song_to_user_weights: defaultdict[str, list[tuple[int, float]]] = (
            defaultdict(list)
        )

        grouped_by_user: defaultdict[int, list[Any]] = defaultdict(list)
        for event in events:
            grouped_by_user[event.user_id].append(event)
            song_to_user_weights[event.song.navidrome_song_id].append(
                (event.user_id, float(event.weight))
            )

        for peer_id, peer_events in grouped_by_user.items():
            if peer_id == user_id:
                continue
            qenet = Counter()
            genres = Counter()
            total_weight = 0.0
            weighted_tempo = 0.0
            acoustic_totals: defaultdict[str, float] = defaultdict(float)
            for event in peer_events:
                weight = max(float(event.weight), 0.1)
                total_weight += weight
                song = event.song
                if song.qenet_mode:
                    qenet[song.qenet_mode] += weight
                if song.genre:
                    genres[song.genre] += weight
                if song.tempo:
                    weighted_tempo += song.tempo * weight
                for key, value in (song.extracted_features or {}).items():
                    if isinstance(value, int | float):
                        acoustic_totals[key] += float(value) * weight
            if total_weight <= 0:
                continue
            user_vectors[peer_id] = TasteVector(
                qenet_mode_affinity={
                    key: value / total_weight for key, value in qenet.items()
                },
                genre_affinity={
                    key: value / total_weight for key, value in genres.items()
                },
                average_tempo=weighted_tempo / total_weight if total_weight else 0.0,
                acoustic_signature={
                    key: value / total_weight for key, value in acoustic_totals.items()
                },
            )

        score = 0.0
        for peer_id, weight in song_to_user_weights.get(song_id, []):
            peer_vector = user_vectors.get(peer_id)
            if peer_vector is None:
                continue
            similarity = self.cosine_similarity(vector, peer_vector)
            score += similarity * weight * 20
        return score

    def rank_for_user(
        self,
        user_id: int,
        songs: list[Any],
        events: list[Any],
        taste_vector: TasteVector,
        heard_song_ids: set[str],
        location: str | None,
        limit: int,
    ) -> list[dict]:
        popularity = PopularityModel()
        location_model = LocationModel()
        scored: list[dict] = []

        for song in songs:
            if song.navidrome_song_id in heard_song_ids:
                continue

            content_score = self._content_affinity(song, taste_vector)
            collaborative_score = self._peer_preference(
                user_id=user_id,
                song_id=song.navidrome_song_id,
                songs=songs,
                events=events,
                vector=taste_vector,
            )
            popularity_score = popularity.score(song)
            regional_score = location_model.score(song, location)

            final_score = (
                content_score * 0.55
                + collaborative_score * 0.25
                + popularity_score * 0.1
                + regional_score * 0.1
            )
            scored.append(
                {
                    "song_id": song.navidrome_song_id,
                    "title": song.title,
                    "artist": song.artist,
                    "genre": song.genre,
                    "qenet_mode": song.qenet_mode,
                    "country": song.country,
                    "score": round(final_score, 4),
                    "score_breakdown": {
                        "content_affinity": round(content_score, 4),
                        "collaborative_filtering": round(collaborative_score, 4),
                        "popularity": round(popularity_score, 4),
                        "regional_context": round(regional_score, 4),
                    },
                }
            )

        return sorted(scored, key=lambda row: row["score"], reverse=True)[:limit]


class TrendingEngine:
    def rank(
        self,
        songs: list[Any],
        events: list[Any],
        playlist_stats: dict[str, Any],
        location: str | None,
        limit: int,
    ) -> list[dict]:
        now = datetime.now(UTC)
        event_totals: defaultdict[str, float] = defaultdict(float)
        regional_totals: defaultdict[str, float] = defaultdict(float)

        for event in events:
            hours_ago = max((now - event.occurred_at).total_seconds() / 3600, 0.0)
            decay = exp(-hours_ago / 6.0)
            weighted = float(event.weight) * decay
            event_totals[event.song.navidrome_song_id] += weighted
            if (
                location
                and event.location
                and event.location.strip().lower() == location.strip().lower()
            ):
                regional_totals[event.song.navidrome_song_id] += weighted

        scored = []
        for song in songs:
            momentum = event_totals.get(song.navidrome_song_id, 0.0)
            regional = regional_totals.get(song.navidrome_song_id, 0.0) * 12.0
            playlist_signal = (
                playlist_stats.get(song.playlist_id) if song.playlist_id else None
            )
            social = (
                ((playlist_signal.save_count if playlist_signal else 0) * 0.8)
                + ((playlist_signal.share_count if playlist_signal else 0) * 0.4)
                + (song.like_count_7d * 0.2)
            )
            hot_score = (
                momentum * 100
                + regional
                + social
                + (song.play_count_7d * 0.05)
                - (song.skip_rate * 10)
            )
            scored.append(
                {
                    "song_id": song.navidrome_song_id,
                    "title": song.title,
                    "artist": song.artist,
                    "genre": song.genre,
                    "qenet_mode": song.qenet_mode,
                    "country": song.country,
                    "hot_score": round(hot_score, 4),
                    "momentum_score": round(momentum * 100, 4),
                    "regional_boost": round(regional, 4),
                    "social_proof": round(social, 4),
                }
            )
        return sorted(scored, key=lambda row: row["hot_score"], reverse=True)[:limit]
