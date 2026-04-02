/* eslint-disable perfectionist/sort-imports */
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import 'overlayscrollbars/overlayscrollbars.css';
import '/styles/overlayscrollbars.css';
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';
import isElectron from 'is-electron';
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';

import i18n from '/@/i18n/i18n';
import {
    registerDevice,
    setBackendAccessToken,
    setBackendUserId,
    telegramLogin,
} from '/@/renderer/api/client';
import { openSettingsModal } from '/@/renderer/features/settings/utils/open-settings-modal';
import { WebAudioContext } from '/@/renderer/features/player/context/webaudio-context';
import { useCheckForUpdates } from '/@/renderer/hooks/use-check-for-updates';
import { useSyncSettingsToMain } from '/@/renderer/hooks/use-sync-settings-to-main';
import { AppRouter } from '/@/renderer/router/app-router';
import {
    useCssSettings,
    useHotkeySettings,
    useLanguage,
    usePlaybackSettings,
    useSettingsStoreActions,
} from '/@/renderer/store';
import { useAppTheme } from '/@/renderer/themes/use-app-theme';
import { detectDeviceClass } from '/@/renderer/utils/device';
import { sanitizeCss } from '/@/renderer/utils/sanitize';
import { getTelegramUserId, isTelegramMiniApp } from '/@/renderer/utils/telegram';
import { WebAudio } from '/@/shared/types/types';
import '/@/shared/styles/global.css';
import '/@/renderer/styles/telegram-lite.css';
import { PlayerProvider } from '/@/renderer/features/player/context/player-context';
import { AudioPlayers } from '/@/renderer/features/player/components/audio-players';

const ReleaseNotesModal = lazy(() =>
    import('./release-notes-modal').then((module) => ({
        default: module.ReleaseNotesModal,
    })),
);

const ipc = isElectron() ? window.api.ipc : null;

export const App = () => {
    const { mode, theme } = useAppTheme();
    const language = useLanguage();

    const { content, enabled } = useCssSettings();
    const { bindings } = useHotkeySettings();
    const playbackSettings = usePlaybackSettings();
    const { setTranscodingConfig } = useSettingsStoreActions();
    const cssRef = useRef<HTMLStyleElement | null>(null);

    useSyncSettingsToMain();
    useCheckForUpdates();

    const [webAudio, setWebAudio] = useState<WebAudio>();
    const telegramMode = isTelegramMiniApp();
    const lowRamMode = detectDeviceClass() === 'lite';

    useEffect(() => {
        document.body.classList.toggle('telegram-lite', telegramMode || lowRamMode);
        document.body.classList.toggle('low-ram-mode', lowRamMode);

        return () => {
            document.body.classList.remove('telegram-lite');
            document.body.classList.remove('low-ram-mode');
        };
    }, [telegramMode, lowRamMode]);

    useEffect(() => {
        let mounted = true;

        const setupDevicePolicy = async () => {
            try {
                const telegramUserId = telegramMode ? getTelegramUserId() : null;
                const response = await registerDevice({
                    telegram: telegramMode,
                    telegram_id: telegramUserId || undefined,
                    user_agent: navigator.userAgent,
                });
                const bitrateMap = {
                    high: 320,
                    lite: 96,
                    standard: 192,
                } as const;
                const bitrate = bitrateMap[response.device_class] ?? 192;

                if (mounted) {
                    setBackendAccessToken(response.access_token);
                    setBackendUserId(response.user_id);
                    if (playbackSettings.transcode.bitrate === bitrate) {
                        return;
                    }
                    setTranscodingConfig({
                        ...playbackSettings.transcode,
                        bitrate,
                        enabled: true,
                    });
                }
            } catch {
                // Keep existing bitrate when backend device registration fails.
            }
        };

        setupDevicePolicy();
        return () => {
            mounted = false;
        };
    }, [playbackSettings.transcode, setTranscodingConfig, telegramMode]);

    useEffect(() => {
        const setupTelegramMode = async () => {
            if (!telegramMode) {
                return;
            }

            const telegramUserId = getTelegramUserId();
            if (!telegramUserId) {
                return;
            }

            localStorage.setItem('telegram-mini-app', 'true');
            localStorage.setItem('telegram-user-id', telegramUserId);

            await telegramLogin({ telegram_user_id: telegramUserId });
        };

        setupTelegramMode();
    }, [telegramMode]);

    useEffect(() => {
        if (enabled && content) {
            // Yes, CSS is sanitized here as well. Prevent a suer from changing the
            // localStorage to bypass sanitizing.
            const sanitized = sanitizeCss(content);
            if (!cssRef.current) {
                cssRef.current = document.createElement('style');
                document.body.appendChild(cssRef.current);
            }

            cssRef.current.textContent = sanitized;

            return () => {
                cssRef.current!.textContent = '';
            };
        }

        return () => {};
    }, [content, enabled]);

    const webAudioProvider = useMemo(() => {
        return { setWebAudio, webAudio };
    }, [webAudio]);

    useEffect(() => {
        if (isElectron()) {
            ipc?.send('set-global-shortcuts', bindings);
        }
    }, [bindings]);

    useEffect(() => {
        if (language) {
            i18n.changeLanguage(language);
        }
    }, [language]);

    useEffect(() => {
        if (isElectron()) {
            window.api.utils.rendererOpenSettings(() => {
                openSettingsModal();
            });

            return () => {
                ipc?.removeAllListeners('renderer-open-settings');
            };
        }
        return undefined;
    }, []);

    const notificationStyles = useMemo(
        () => ({
            root: {
                marginBottom: 90,
            },
        }),
        [],
    );

    return (
        <MantineProvider forceColorScheme={mode} theme={theme}>
            <Notifications
                containerWidth="300px"
                position="bottom-center"
                styles={notificationStyles}
                zIndex={50000}
            />
            <WebAudioContext.Provider value={webAudioProvider}>
                <PlayerProvider>
                    <AudioPlayers />
                    <AppRouter />
                </PlayerProvider>
            </WebAudioContext.Provider>
            <Suspense fallback={null}>
                <ReleaseNotesModal />
            </Suspense>
        </MantineProvider>
    );
};
