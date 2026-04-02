import isElectron from 'is-electron';

import { getServerById, } from '/@/renderer/store';
import { QueueSong } from '/@/shared/types/domain-types';

const remote = isElectron() ? window.api.remote : null;
const mediaSession = navigator.mediaSession;

export const updateSong = (song: QueueSong | undefined, imageUrl?: null | string) => {
    if (mediaSession) {
        let metadata: MediaMetadata;

        if (song?.id) {
            let artwork: MediaImage[];

            if (imageUrl) {
                artwork = [{ sizes: '300x300', src: imageUrl, type: 'image/png' }];
            } else {
                artwork = [];
            }

            metadata = new MediaMetadata({
                album: song.album ?? '',
                artist: song.artistName,
                artwork,
                title: song.name,
            });
        } else {
            metadata = new MediaMetadata();
        }

        mediaSession.metadata = metadata;
    }

    const allowedImageOrigin = song?._serverId
        ? (() => {
              const server = getServerById(song._serverId);
              if (!server) {
                  return null;
              }

              try {
                  return new URL(server.url).origin;
              } catch {
                  return null;
              }
          })()
        : null;

    remote?.updateSong(song, imageUrl, allowedImageOrigin);
};
