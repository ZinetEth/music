import { openModal } from '@mantine/modals';
import { useEffect, useMemo, useRef, useState } from 'react';

import { api } from '/@/renderer/api';
import { canPlaySong, getBackendUserId } from '/@/renderer/api/client';
import { TranscodingConfig } from '/@/renderer/store';
import { Text } from '/@/shared/components/text/text';
import { toast } from '/@/shared/components/toast/toast';
import { QueueSong } from '/@/shared/types/domain-types';

export function useSongUrl(
    song: QueueSong | undefined,
    current: boolean,
    transcode: TranscodingConfig,
): string | undefined {
    const prior = useRef(['', '']);
    const [allowedToPlay, setAllowedToPlay] = useState(true);

    useEffect(() => {
        let mounted = true;

        const validatePlaybackAccess = async () => {
            if (!song) {
                if (mounted) setAllowedToPlay(true);
                return;
            }

            try {
                const userId = getBackendUserId();
                const result = await canPlaySong(userId, song.id);
                const allowed = Boolean(result?.allowed);

                if (!allowed) {
                    openModal({
                        children: <Text>Buy this song or subscribe to unlock playback.</Text>,
                        title: 'Playback Locked',
                    });
                    toast.warn({
                        message: 'purchase or subscription required',
                        title: 'Playback',
                    });
                }
                if (mounted) setAllowedToPlay(allowed);
            } catch (error: unknown) {
                toast.error({
                    message: error instanceof Error ? error.message : 'network error',
                    title: 'Playback',
                });
                if (mounted) setAllowedToPlay(false);
            }
        };

        validatePlaybackAccess();
        return () => {
            mounted = false;
        };
    }, [song, song?._uniqueId, song?.name]);

    return useMemo(() => {
        if (!allowedToPlay) {
            return undefined;
        }

        if (song?._serverId) {
            // If we are the current track, we do not want a transcoding
            // reconfiguration to force a restart.
            if (current && prior.current[0] === song._uniqueId) {
                return prior.current[1];
            }

            const url = api.controller.getStreamUrl({
                apiClientProps: { serverId: song._serverId },
                query: {
                    bitrate: transcode.bitrate,
                    format: transcode.format,
                    id: song.id,
                    transcode: transcode.enabled,
                },
            });

            // transcoding enabled; save the updated result
            prior.current = [song._uniqueId, url];
            return url;
        }

        // no track; clear result
        prior.current = ['', ''];
        return undefined;
    }, [
        allowedToPlay,
        song?._serverId,
        song?._uniqueId,
        song?.id,
        current,
        transcode.bitrate,
        transcode.format,
        transcode.enabled,
    ]);
}

export const getSongUrl = (song: QueueSong, transcode: TranscodingConfig) => {
    return api.controller.getStreamUrl({
        apiClientProps: { serverId: song._serverId },
        query: {
            bitrate: transcode.bitrate,
            format: transcode.format,
            id: song.id,
            transcode: transcode.enabled,
        },
    });
};
