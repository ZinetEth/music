'use strict';

const isWebRuntime = /^https?:$/i.test(window.location.protocol);

window.SERVER_URL = isWebRuntime ? `${window.location.origin}/navidrome` : 'http://127.0.0.1:4533';
window.SERVER_NAME = 'Music';
window.SERVER_TYPE = 'navidrome';
window.SERVER_USERNAME = 'admin';
window.SERVER_PASSWORD = 'MusicApp!2026';
window.SERVER_LOCK = 'true';
window.LEGACY_AUTHENTICATION = 'false';
window.ANALYTICS_DISABLED = 'true';
