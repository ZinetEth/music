import { lazy } from 'react';
import { Navigate, Route } from 'react-router';

import { ConsumerShell } from '/@/renderer/features/consumer/layout';
import { AppRoute } from '/@/renderer/router/routes';
import { isTelegramMiniApp } from '/@/renderer/utils/telegram';

const NowPlayingRoute = lazy(
    () => import('/@/renderer/features/consumer/screens/now-playing-screen'),
);
const HomeRoute = lazy(() => import('/@/renderer/features/consumer/screens/home-screen'));
const ConsumerSearchRoute = lazy(
    () => import('/@/renderer/features/consumer/screens/search-screen'),
);
const ConsumerLibraryRoute = lazy(
    () => import('/@/renderer/features/consumer/screens/library-screen'),
);
const MarketplacePage = lazy(() => import('/@/renderer/pages/Marketplace'));
const PaymentsPage = lazy(() => import('/@/renderer/pages/Payments'));
const ProfilePage = lazy(() => import('/@/renderer/pages/Profile'));

const MOBILE_BREAKPOINT = 768;

const getInitialConsumerRoute = () => {
    if (isTelegramMiniApp()) {
        return AppRoute.HOME;
    }

    if (typeof window !== 'undefined' && window.matchMedia) {
        const isMobile = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`).matches;
        return isMobile ? AppRoute.HOME : AppRoute.NOW_PLAYING;
    }

    return AppRoute.HOME;
};

const InitialLandingRoute = () => <Navigate replace to={getInitialConsumerRoute()} />;

export const consumerRoutes = (
    <Route element={<ConsumerShell />}>
        <Route element={<InitialLandingRoute />} index />
        <Route element={<HomeRoute />} path={AppRoute.HOME} />
        <Route element={<ConsumerSearchRoute />} path={AppRoute.SEARCH} />
        <Route element={<ConsumerLibraryRoute />} path={AppRoute.LIBRARY} />
        <Route element={<NowPlayingRoute />} path={AppRoute.NOW_PLAYING} />
        <Route element={<HomeRoute />} path={AppRoute.FAVORITES} />
        <Route element={<HomeRoute />} path={AppRoute.SETTINGS} />
        <Route element={<MarketplacePage />} path={AppRoute.MARKETPLACE} />
        <Route element={<PaymentsPage />} path={AppRoute.PAYMENTS} />
        <Route element={<ProfilePage />} path={AppRoute.PROFILE} />
        <Route element={<HomeRoute />} path="*" />
    </Route>
);
