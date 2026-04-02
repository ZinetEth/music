import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';

import styles from './consumer-screens.module.css';

import {
    getBackendUserId,
    getRecommendations,
    getTrending,
    type RecommendationSong,
    type TrendingSong,
} from '/@/renderer/api/client';
import { AppRoute } from '/@/renderer/router/routes';

type LookalikeUser = {
    similarity: number;
    user_id: number;
};

const cardMetaStyle = {
    color: 'rgb(255 255 255 / 68%)',
    display: 'grid',
    gap: 4,
} as const;

export default function HomeScreen() {
    const navigate = useNavigate();
    const backendUserId = getBackendUserId();
    const [forYou, setForYou] = useState<RecommendationSong[]>([]);
    const [trending, setTrending] = useState<TrendingSong[]>([]);
    const [lookalikes, setLookalikes] = useState<LookalikeUser[]>([]);
    const [loading, setLoading] = useState(true);

    const greeting = useMemo(() => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 18) return 'Good afternoon';
        return 'Good evening';
    }, []);

    useEffect(() => {
        let mounted = true;

        const load = async () => {
            setLoading(true);
            try {
                const [forYouFeed, trendingFeed] = await Promise.all([
                    getRecommendations(backendUserId),
                    getTrending('Ethiopia'),
                ]);

                if (!mounted) {
                    return;
                }

                setForYou(forYouFeed.recommendations);
                setLookalikes(forYouFeed.lookalike_audience);
                setTrending(trendingFeed.recommendations);
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        };

        load();
        return () => {
            mounted = false;
        };
    }, [backendUserId]);

    return (
        <div className={styles.screen}>
            <div className={styles.hero}>
                <div>
                    <div className={styles.eyebrow}>For you</div>
                    <h1>{greeting}</h1>
                    <p>Your music, personalized from listening habits and live momentum.</p>
                </div>
                <button
                    className={styles.searchShortcut}
                    onClick={() => navigate(AppRoute.SEARCH)}
                    type="button"
                >
                    Search music
                </button>
            </div>

            <InsightRow lookalikes={lookalikes} loading={loading} />
            <SongSection
                items={forYou}
                loading={loading}
                onOpenMarketplace={() => navigate(AppRoute.MARKETPLACE)}
                title="Made For You"
            />
            <TrendingSection items={trending} loading={loading} title="Trending Right Now" />
        </div>
    );
}

function InsightRow({
    loading,
    lookalikes,
}: {
    loading: boolean;
    lookalikes: LookalikeUser[];
}) {
    return (
        <section className={styles.section}>
            <div className={styles.sectionHeader}>
                <h2>Taste Insights</h2>
            </div>
            <div className={styles.horizontalRail}>
                {loading && <div className={styles.cardButton}>Loading your profile...</div>}
                {!loading &&
                    lookalikes.map((item) => (
                        <div className={styles.cardButton} key={item.user_id}>
                            <div style={cardMetaStyle}>
                                <strong>Listener #{item.user_id}</strong>
                                <span>{Math.round(item.similarity * 100)}% taste match</span>
                            </div>
                        </div>
                    ))}
            </div>
        </section>
    );
}

function SongSection({
    items,
    loading,
    onOpenMarketplace,
    title,
}: {
    items: RecommendationSong[];
    loading: boolean;
    onOpenMarketplace: () => void;
    title: string;
}) {
    return (
        <section className={styles.section}>
            <div className={styles.sectionHeader}>
                <h2>{title}</h2>
            </div>
            <div className={styles.horizontalRail}>
                {loading && <div className={styles.cardButton}>Loading recommendations...</div>}
                {!loading &&
                    items.map((item) => (
                        <button
                            className={styles.cardButton}
                            key={item.song_id}
                            onClick={onOpenMarketplace}
                            type="button"
                        >
                            <div style={cardMetaStyle}>
                                <strong>{item.title}</strong>
                                <span>
                                    {item.artist} | {item.genre}
                                </span>
                                <span>
                                    Match {item.score.toFixed(1)}
                                    {item.qenet_mode ? ` | ${item.qenet_mode}` : ''}
                                </span>
                            </div>
                        </button>
                    ))}
            </div>
        </section>
    );
}

function TrendingSection({
    items,
    loading,
    title,
}: {
    items: TrendingSong[];
    loading: boolean;
    title: string;
}) {
    return (
        <section className={styles.section}>
            <div className={styles.sectionHeader}>
                <h2>{title}</h2>
            </div>
            <div className={styles.horizontalRail}>
                {loading && <div className={styles.cardButton}>Loading trends...</div>}
                {!loading &&
                    items.map((item) => (
                        <div className={styles.cardButton} key={item.song_id}>
                            <div style={cardMetaStyle}>
                                <strong>{item.title}</strong>
                                <span>
                                    {item.artist}
                                    {item.country ? ` | ${item.country}` : ''}
                                </span>
                                <span>
                                    Hot {item.hot_score.toFixed(1)} | Momentum{' '}
                                    {item.momentum_score.toFixed(1)}
                                </span>
                            </div>
                        </div>
                    ))}
            </div>
        </section>
    );
}
