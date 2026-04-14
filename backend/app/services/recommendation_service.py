from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from math import exp, sqrt

from sqlalchemy.orm import Session

from app import models, schemas
from app.repositories.recommendation_repo import RecommendationRepository
from app.utils.helpers import gregorian_to_ethiopian


@dataclass
class TasteVector:
    qenet_mode_affinity: dict[str, float]
    genre_affinity: dict[str, float]
    average_tempo: float
    acoustic_signature: dict[str, float]


@dataclass
class RankedSong:
    song: models.LibrarySong
    score: float
    score_breakdown: dict[str, float]


class FastRecommendationLayer:
    """Fetch a lightweight candidate pool from persisted user and song activity."""

    def __init__(self, repository: RecommendationRepository):
        self.repository = repository

    def fetch_candidates(self, user_id: int, limit: int = 200) -> list[models.LibrarySong]:
        unheard = self.repository.songs.list_unheard_for_user(user_id, limit=limit)
        if unheard:
            return unheard
        return self.repository.songs.list_catalog(limit=limit)

    def detect_holiday_rule(self, target_date: date) -> models.HolidayRule | None:
        _eth_year, eth_month, eth_day = gregorian_to_ethiopian(
            target_date.year,
            target_date.month,
            target_date.day,
        )
        for rule in self.repository.songs.list_active_holiday_rules():
            if rule.eth_month == eth_month and rule.eth_day == eth_day:
                return rule
        return None


class RankingEngine:
    """Rank candidates with personal, collaborative, freshness, and context signals."""

    def __init__(self, repository: RecommendationRepository):
        self.repository = repository

    def build_taste_vector(self, user: models.User) -> TasteVector:
        safe = user.taste_vector or {}
        return TasteVector(
            qenet_mode_affinity={
                key: float(value)
                for key, value in safe.get("qenet_mode_affinity", {}).items()
            },
            genre_affinity={
                key: float(value)
                for key, value in safe.get("genre_affinity", {}).items()
            },
            average_tempo=float(safe.get("average_tempo", 0.0)),
            acoustic_signature={
                key: float(value)
                for key, value in safe.get("acoustic_signature", {}).items()
            },
        )

    def rank(
        self,
        *,
        user: models.User,
        candidates: list[models.LibrarySong],
        location: str | None,
        target_date: date,
        holiday_rule: models.HolidayRule | None,
    ) -> list[RankedSong]:
        vector = self.build_taste_vector(user)
        peer_events = self.repository.playback.list_recent_events(hours=24 * 30)
        peer_vectors = self._build_peer_vectors(user.id, peer_events)
        holiday_key = holiday_rule.key if holiday_rule else None

        ranked: list[RankedSong] = []
        for song in candidates:
            content_affinity = self._content_affinity(song, vector)
            collaborative = self._peer_preference(song, peer_events, vector, peer_vectors)
            popularity = self._popularity(song)
            recency = self._recency(song, target_date)
            regional = self._regional(song, location)
            seasonal = self._seasonal(song, holiday_key)

            final_score = (
                content_affinity * 0.38
                + collaborative * 0.22
                + popularity * 0.16
                + recency * 0.10
                + regional * 0.08
                + seasonal * 0.06
            )
            ranked.append(
                RankedSong(
                    song=song,
                    score=round(final_score, 4),
                    score_breakdown={
                        "content_affinity": round(content_affinity, 4),
                        "collaborative_filtering": round(collaborative, 4),
                        "popularity": round(popularity, 4),
                        "recency": round(recency, 4),
                        "regional_context": round(regional, 4),
                        "seasonal_context": round(seasonal, 4),
                    },
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked

    def _content_affinity(self, song: models.LibrarySong, vector: TasteVector) -> float:
        score = 0.0
        if song.qenet_mode:
            score += vector.qenet_mode_affinity.get(song.qenet_mode, 0.0) * 100
        if song.genre:
            score += vector.genre_affinity.get(song.genre, 0.0) * 80
        if vector.average_tempo and song.tempo:
            tempo_distance = abs(vector.average_tempo - song.tempo)
            score += max(0.0, 30.0 - min(tempo_distance / 2.0, 30.0))

        for key, preference in vector.acoustic_signature.items():
            raw = (song.extracted_features or {}).get(key)
            if isinstance(raw, int | float):
                score += max(0.0, 20.0 - abs(preference - float(raw)) * 10)
        return score

    def _build_peer_vectors(
        self,
        user_id: int,
        events: list[models.PlaybackEvent],
    ) -> dict[int, TasteVector]:
        grouped_by_user: defaultdict[int, list[models.PlaybackEvent]] = defaultdict(list)
        for event in events:
            if event.user_id != user_id:
                grouped_by_user[event.user_id].append(event)

        vectors: dict[int, TasteVector] = {}
        for peer_id, peer_events in grouped_by_user.items():
            qenet = Counter()
            genres = Counter()
            acoustic_totals: defaultdict[str, float] = defaultdict(float)
            total_weight = 0.0
            weighted_tempo = 0.0

            for event in peer_events:
                weight = max(float(event.weight), 0.1)
                total_weight += weight
                if event.song.qenet_mode:
                    qenet[event.song.qenet_mode] += weight
                if event.song.genre:
                    genres[event.song.genre] += weight
                if event.song.tempo:
                    weighted_tempo += event.song.tempo * weight
                for key, value in (event.song.extracted_features or {}).items():
                    if isinstance(value, int | float):
                        acoustic_totals[key] += float(value) * weight

            if total_weight <= 0:
                continue

            vectors[peer_id] = TasteVector(
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

        return vectors

    def _peer_preference(
        self,
        song: models.LibrarySong,
        events: list[models.PlaybackEvent],
        vector: TasteVector,
        peer_vectors: dict[int, TasteVector],
    ) -> float:
        score = 0.0
        for event in events:
            if event.song.navidrome_song_id != song.navidrome_song_id:
                continue
            peer_vector = peer_vectors.get(event.user_id)
            if peer_vector is None:
                continue
            score += self._cosine_similarity(vector, peer_vector) * float(event.weight) * 20
        return score

    def _cosine_similarity(self, left: TasteVector, right: TasteVector) -> float:
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
        right_values["tempo"] = right.average_tempo / 220.0 if right.average_tempo else 0.0

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

    def _popularity(self, song: models.LibrarySong) -> float:
        return (
            (song.play_count_7d * 0.6)
            + (song.like_count_7d * 1.8)
            - (song.skip_rate * 20.0)
        )

    def _recency(self, song: models.LibrarySong, target_date: date) -> float:
        if not song.release_date:
            return 0.0
        try:
            released = datetime.strptime(song.release_date, "%Y-%m-%d").date()
        except ValueError:
            return 0.0
        age_days = max((target_date - released).days, 0)
        return exp(-age_days / 45.0) * 100.0

    def _regional(self, song: models.LibrarySong, location: str | None) -> float:
        if not location or not song.country:
            return 0.0
        return 35.0 if location.strip().lower() == song.country.strip().lower() else 0.0

    def _seasonal(self, song: models.LibrarySong, holiday_key: str | None) -> float:
        if not holiday_key:
            return 0.0
        haystacks = [
            song.navidrome_song_id.lower(),
            (song.playlist_id or "").lower(),
            song.genre.lower(),
        ]
        if any(holiday_key.lower() in haystack for haystack in haystacks):
            return 40.0
        if song.genre.lower() in {"traditional", "gospel"}:
            return 10.0
        return 0.0


class SessionOptimizer:
    """Re-order top candidates to encourage longer continuous listening."""

    def __init__(self, repository: RecommendationRepository):
        self.repository = repository

    def optimize(
        self,
        *,
        user_id: int,
        ranked_songs: list[RankedSong],
        limit: int,
    ) -> tuple[list[RankedSong], models.ListeningSession]:
        session = self.repository.playback.get_or_start_session(user_id)
        recent_history = self.repository.playback.list_recent_events_for_user(
            user_id,
            hours=6,
            limit=10,
        )

        optimized: list[RankedSong] = []
        recent_artists = [event.song.artist for event in recent_history]
        recent_genres = [event.song.genre for event in recent_history]
        recent_tempos = [event.song.tempo for event in recent_history if event.song.tempo]

        remaining = ranked_songs[:]
        while remaining and len(optimized) < limit:
            best_index = 0
            best_score = float("-inf")

            for index, candidate in enumerate(remaining):
                adjusted = candidate.score + self._continuation_bonus(
                    candidate.song,
                    recent_artists=recent_artists,
                    recent_genres=recent_genres,
                    recent_tempos=recent_tempos,
                    queued=optimized,
                )
                if adjusted > best_score:
                    best_score = adjusted
                    best_index = index

            chosen = remaining.pop(best_index)
            optimized.append(chosen)
            recent_artists.append(chosen.song.artist)
            recent_genres.append(chosen.song.genre)
            if chosen.song.tempo:
                recent_tempos.append(chosen.song.tempo)

        self.repository.playback.replace_session_recommendations(
            session.id,
            [(item.song.navidrome_song_id, item.score) for item in optimized],
        )
        return optimized, session

    def _continuation_bonus(
        self,
        song: models.LibrarySong,
        *,
        recent_artists: list[str],
        recent_genres: list[str],
        recent_tempos: list[float],
        queued: list[RankedSong],
    ) -> float:
        bonus = 0.0
        if recent_artists and song.artist != recent_artists[-1]:
            bonus += 4.0
        elif recent_artists:
            bonus -= 8.0

        if recent_genres and song.genre == recent_genres[-1]:
            bonus += 2.0
        elif recent_genres:
            bonus += 1.0

        if recent_tempos and song.tempo:
            tempo_delta = abs(song.tempo - recent_tempos[-1])
            bonus += max(-6.0, 6.0 - (tempo_delta / 8.0))

        if queued and queued[-1].song.navidrome_song_id == song.navidrome_song_id:
            bonus -= 50.0

        return bonus


class RecommendationService:
    def __init__(self, db: Session):
        self.repository = RecommendationRepository(db)
        self.fast_layer = FastRecommendationLayer(self.repository)
        self.ranking_engine = RankingEngine(self.repository)
        self.session_optimizer = SessionOptimizer(self.repository)

    def get_personalized_feed(
        self,
        *,
        user_id: int,
        location: str | None,
        limit: int,
        target_date: date | None = None,
    ) -> schemas.PersonalizedFeedResponse:
        user = self.repository.users.get_by_id(user_id)
        if user is None:
            raise ValueError("user_not_found")

        target = target_date or date.today()
        candidates = self.fast_layer.fetch_candidates(
            user_id=user_id,
            limit=max(limit * 8, 40),
        )
        holiday_rule = self.fast_layer.detect_holiday_rule(target)
        ranked = self.ranking_engine.rank(
            user=user,
            candidates=candidates,
            location=location,
            target_date=target,
            holiday_rule=holiday_rule,
        )
        optimized, session = self.session_optimizer.optimize(
            user_id=user_id,
            ranked_songs=ranked,
            limit=limit,
        )

        vector = self.ranking_engine.build_taste_vector(user)
        lookalikes = self._lookalikes(user_id, vector)
        return schemas.PersonalizedFeedResponse(
            user_id=user_id,
            location=location,
            model_backend="fast_rank_session_v1",
            taste_vector=schemas.TasteVectorOut(
                qenet_mode_affinity=vector.qenet_mode_affinity,
                genre_affinity=vector.genre_affinity,
                average_tempo=round(vector.average_tempo, 2),
                acoustic_signature={
                    key: round(value, 4)
                    for key, value in vector.acoustic_signature.items()
                },
            ),
            lookalike_audience=lookalikes,
            recommendations=[
                schemas.SongRecommendationOut(
                    song_id=item.song.navidrome_song_id,
                    title=item.song.title,
                    artist=item.song.artist,
                    genre=item.song.genre,
                    qenet_mode=item.song.qenet_mode,
                    country=item.song.country,
                    score=item.score,
                    score_breakdown=item.score_breakdown
                    | {"session_id": float(session.id)},
                )
                for item in optimized
            ],
        )

    def get_hybrid_feed(
        self,
        *,
        location: str | None,
        limit: int,
        target_date: date | None = None,
        user_id: int | None = None,
    ) -> schemas.HybridRecommendationResponse:
        target = target_date or date.today()
        catalog = (
            self.repository.songs.list_unheard_for_user(user_id, limit=max(limit * 8, 40))
            if user_id
            else self.repository.songs.list_catalog(limit=max(limit * 8, 40))
        )
        holiday_rule = self.fast_layer.detect_holiday_rule(target)
        reference_user = self.repository.users.get_by_id(user_id) if user_id else None
        if reference_user is None:
            reference_user = models.User(
                taste_vector={},
                device_class="standard",
                is_telegram_user=False,
            )

        ranked = self.ranking_engine.rank(
            user=reference_user,
            candidates=catalog,
            location=location,
            target_date=target,
            holiday_rule=holiday_rule,
        )[:limit]

        return schemas.HybridRecommendationResponse(
            date=target.isoformat(),
            holiday=holiday_rule.key if holiday_rule else None,
            location=location,
            model_backend="fast_rank_session_v1",
            recommendations=[
                schemas.SongRecommendationOut(
                    song_id=item.song.navidrome_song_id,
                    title=item.song.title,
                    artist=item.song.artist,
                    genre=item.song.genre,
                    qenet_mode=item.song.qenet_mode,
                    country=item.song.country,
                    score=item.score,
                    score_breakdown=item.score_breakdown,
                )
                for item in ranked
            ],
        )

    def recommend_playlists(
        self,
        *,
        target_date: date | None = None,
    ) -> schemas.PlaylistRecommendationResponse:
        target = target_date or date.today()
        holiday_rule = self.fast_layer.detect_holiday_rule(target)
        recommendations = [
            schemas.PlaylistRecommendation(**item)
            for item in (holiday_rule.recommendations if holiday_rule else [])
        ]
        return schemas.PlaylistRecommendationResponse(
            date=target.isoformat(),
            holiday=holiday_rule.key if holiday_rule else None,
            recommendations=recommendations,
        )

    def get_trending_feed(
        self,
        *,
        location: str | None,
        limit: int,
    ) -> schemas.TrendingFeedResponse:
        songs = self.repository.songs.list_catalog(limit=max(limit * 8, 40))
        playlist_stats = self.repository.songs.list_playlist_signals()
        events = self.repository.playback.list_recent_events(hours=24 * 7)
        now = datetime.utcnow()

        event_totals: defaultdict[str, float] = defaultdict(float)
        regional_totals: defaultdict[str, float] = defaultdict(float)
        for event in events:
            occurred_at = event.occurred_at.replace(tzinfo=None)
            hours_ago = max((now - occurred_at).total_seconds() / 3600, 0.0)
            decay = exp(-hours_ago / 6.0)
            weighted = float(event.weight) * decay
            event_totals[event.song.navidrome_song_id] += weighted
            if (
                location
                and event.location
                and event.location.strip().lower() == location.strip().lower()
            ):
                regional_totals[event.song.navidrome_song_id] += weighted

        scored: list[schemas.TrendingSongOut] = []
        for song in songs:
            playlist_signal = (
                playlist_stats.get(song.playlist_id) if song.playlist_id else None
            )
            momentum = event_totals.get(song.navidrome_song_id, 0.0)
            regional = regional_totals.get(song.navidrome_song_id, 0.0) * 12.0
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
                schemas.TrendingSongOut(
                    song_id=song.navidrome_song_id,
                    title=song.title,
                    artist=song.artist,
                    genre=song.genre,
                    qenet_mode=song.qenet_mode,
                    country=song.country,
                    hot_score=round(hot_score, 4),
                    momentum_score=round(momentum * 100, 4),
                    regional_boost=round(regional, 4),
                    social_proof=round(social, 4),
                )
            )

        scored.sort(key=lambda item: item.hot_score, reverse=True)
        return schemas.TrendingFeedResponse(
            location=location,
            generated_at=datetime.utcnow().isoformat(),
            recommendations=scored[:limit],
        )

    def _lookalikes(
        self,
        user_id: int,
        vector: TasteVector,
    ) -> list[schemas.LookalikeUserOut]:
        results: list[schemas.LookalikeUserOut] = []
        for peer in self.repository.users.list_peers(user_id):
            peer_vector = self.ranking_engine.build_taste_vector(peer)
            similarity = self.ranking_engine._cosine_similarity(vector, peer_vector)
            if similarity > 0:
                results.append(
                    schemas.LookalikeUserOut(
                        user_id=peer.id,
                        similarity=round(similarity, 4),
                    )
                )
        return sorted(results, key=lambda item: item.similarity, reverse=True)[:5]
