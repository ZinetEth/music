/**
 * Setup Music Platform Server in Feishin
 * 
 * Run this script to configure Feishin to connect to our backend
 * instead of looking for Navidrome or other servers.
 */

// Music Platform Server Configuration
const musicPlatformServer = {
    id: 'music-platform-backend',
    name: 'Music Platform Backend',
    type: 'music-platform',
    url: 'http://localhost:8000',
    credential: 'default-credential',
    features: {
        music_platform: {
            library: true,
            playlists: true,
            albums: true,
            artists: true,
            genres: true,
            tracks: true,
            folders: false,
            share: false,
            upload: false,
            rescan: false,
            rating: false,
            comment: false,
            lyrics: false,
        }
    },
    isDefault: true,
    isAdmin: true,
    version: '1.0.0',
    ndCredential: 'default-credential'
};

// Instructions
console.log('🎵 Music Platform Server Setup');
console.log('');
console.log('To configure Feishin to connect to our music platform backend:');
console.log('');
console.log('1. Open Feishin application');
console.log('2. Go to Settings > Servers');
console.log('3. Add a new server with these details:');
console.log('');
console.log('Server Details:');
console.log(JSON.stringify(musicPlatformServer, null, 2));
console.log('');
console.log('Or run this in browser console:');
console.log(`localStorage.setItem('auth-store', JSON.stringify({`);
console.log(`  currentServer: ${JSON.stringify(musicPlatformServer)},`);
console.log(`  serverList: ${JSON.stringify({ 'music-platform-backend': musicPlatformServer })},`);
console.log(`  deviceId: 'default-device-id'`);
console.log(`}));`);
console.log('');
console.log('Then refresh the page!');
