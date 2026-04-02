import { useEffect, useState } from 'react';

import {
    getBackendUserId,
    getMarketplacePlaylists,
    getMarketplaceSongs,
    getSecurePlaylistAccess,
    getSecureSongAccess,
    MarketplaceSong,
    MarketplacePlaylist,
    purchaseSong,
    purchasePlaylist,
    savePlaylist,
} from '/@/renderer/api/client';
import { Button } from '/@/shared/components/button/button';
import { Group } from '/@/shared/components/group/group';
import { Stack } from '/@/shared/components/stack/stack';
import { Text } from '/@/shared/components/text/text';
import { toast } from '/@/shared/components/toast/toast';

const MarketplacePage = () => {
    const userId = getBackendUserId();
    const [playlists, setPlaylists] = useState<MarketplacePlaylist[]>([]);
    const [songs, setSongs] = useState<MarketplaceSong[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let mounted = true;
        const load = async () => {
            setLoading(true);
            try {
                const [playlistData, songData] = await Promise.all([
                    getMarketplacePlaylists(),
                    getMarketplaceSongs(),
                ]);
                if (mounted) {
                    setPlaylists(playlistData);
                    setSongs(songData);
                }
            } catch (error: any) {
                toast.error({ message: error?.message || 'network error', title: 'Marketplace' });
            } finally {
                if (mounted) setLoading(false);
            }
        };
        load();
        return () => {
            mounted = false;
        };
    }, []);

    const handleBuy = async (playlistId: string) => {
        try {
            await purchasePlaylist(userId, playlistId);
            toast.success({ message: 'Playlist purchased successfully', title: 'Marketplace' });
        } catch (error: any) {
            toast.error({ message: error?.message || 'payment failed', title: 'Marketplace' });
        }
    };

    const handleSave = async (playlistId: string) => {
        try {
            const result = await savePlaylist(userId, playlistId);
            setPlaylists((current) =>
                current.map((item) =>
                    item.playlist_id === playlistId
                        ? { ...item, save_count: result.save_count }
                        : item,
                ),
            );
            toast.success({ message: 'Playlist saved to your profile', title: 'Marketplace' });
        } catch (error: any) {
            toast.error({ message: error?.message || 'save failed', title: 'Marketplace' });
        }
    };

    const handlePreview = async (playlistId: string) => {
        try {
            const result = await getSecurePlaylistAccess(userId, playlistId);
            if (!result.authorized) {
                toast.warn({
                    message: 'Buy this playlist first to unlock secure streaming.',
                    title: 'Marketplace',
                });
                return;
            }
            toast.success({
                message: result.stream_path || result.x_accel_redirect || 'Secure stream unlocked',
                title: 'Marketplace',
            });
        } catch (error: any) {
            toast.error({ message: error?.message || 'preview failed', title: 'Marketplace' });
        }
    };

    const handleBuySong = async (songId: string) => {
        try {
            const result = await purchaseSong(userId, songId);
            setSongs((current) =>
                current.map((item) =>
                    item.song_id === songId ? { ...item, sales_count: result.sales_count } : item,
                ),
            );
            toast.success({ message: 'Song purchased successfully', title: 'Marketplace' });
        } catch (error: any) {
            toast.error({ message: error?.message || 'payment failed', title: 'Marketplace' });
        }
    };

    const handleUnlockSong = async (songId: string) => {
        try {
            const result = await getSecureSongAccess(userId, songId);
            if (!result.authorized) {
                toast.warn({
                    message: 'Buy this song or subscribe first to unlock playback.',
                    title: 'Marketplace',
                });
                return;
            }
            toast.success({
                message: result.stream_path || 'Song stream unlocked',
                title: 'Marketplace',
            });
        } catch (error: any) {
            toast.error({ message: error?.message || 'unlock failed', title: 'Marketplace' });
        }
    };

    return (
        <Stack gap="md" p="lg">
            <Text fw={700} size="xl">
                Marketplace
            </Text>
            {loading && <Text variant="secondary">Loading marketplace...</Text>}
            {!loading && (
                <>
                    <Text fw={600} size="lg">
                        Playlists
                    </Text>
                    {playlists.map((playlist) => (
                    <Stack
                        className="telegram-panel"
                        gap="xs"
                        key={playlist.playlist_id}
                        p="md"
                        style={{
                            background: 'var(--theme-colors-surface)',
                            borderRadius: 12,
                        }}
                    >
                        <Text fw={600}>{playlist.title}</Text>
                        <Text variant="secondary">Creator: {playlist.creator_name}</Text>
                        <Text variant="secondary">
                            Artist: {playlist.artist_name || 'Independent creator'}
                            {playlist.artist_verified ? ' • Verified' : ''}
                        </Text>
                        <Text variant="secondary">
                            Price: {playlist.currency} {playlist.price}
                        </Text>
                        <Text variant="secondary">
                            Saves: {playlist.save_count} • Sales: {playlist.sales_count} • Score:{' '}
                            {playlist.social_score.toFixed(1)}
                        </Text>
                        <Group>
                            <Button
                                onClick={() => handlePreview(playlist.playlist_id)}
                                variant="default"
                            >
                                Secure Access
                            </Button>
                            <Button onClick={() => handleSave(playlist.playlist_id)} variant="default">
                                Save
                            </Button>
                            <Button
                                className="telegram-primary-btn"
                                onClick={() => handleBuy(playlist.playlist_id)}
                            >
                                Buy Playlist
                            </Button>
                        </Group>
                    </Stack>
                    ))}
                    <Text fw={600} mt="md" size="lg">
                        Songs
                    </Text>
                    {songs.map((song) => (
                        <Stack
                            className="telegram-panel"
                            gap="xs"
                            key={song.song_id}
                            p="md"
                            style={{
                                background: 'var(--theme-colors-surface)',
                                borderRadius: 12,
                            }}
                        >
                            <Text fw={600}>{song.title}</Text>
                            <Text variant="secondary">Artist: {song.artist}</Text>
                            <Text variant="secondary">
                                Genre: {song.genre}
                                {song.is_premium ? ' • Premium' : ''}
                            </Text>
                            <Text variant="secondary">
                                Price: {song.currency} {song.price}
                            </Text>
                            <Text variant="secondary">
                                Plays: {song.play_count_7d} • Likes: {song.like_count_7d} • Sales:{' '}
                                {song.sales_count}
                            </Text>
                            <Group>
                                <Button onClick={() => handleUnlockSong(song.song_id)} variant="default">
                                    Unlock Stream
                                </Button>
                                <Button
                                    className="telegram-primary-btn"
                                    onClick={() => handleBuySong(song.song_id)}
                                >
                                    Buy Song
                                </Button>
                            </Group>
                        </Stack>
                    ))}
                </>
            )}
        </Stack>
    );
};

export default MarketplacePage;
