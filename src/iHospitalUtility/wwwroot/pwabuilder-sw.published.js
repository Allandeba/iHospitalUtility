// Based on the Blazor PWA template: cache one complete published release.
self.importScripts('./service-worker-assets.js');

const CACHE_PREFIX = 'ihospitalutility-offline-';
const CACHE_NAME = CACHE_PREFIX + self.assetsManifest.version;
const SCOPE = new URL(self.registration.scope);
const ASSETS = self.assetsManifest.assets.map(asset => ({
    url: new URL(asset.url, SCOPE).href,
    hash: asset.hash,
}));
const ASSET_URLS = new Set(ASSETS.map(asset => asset.url));
const INDEX_URL = new URL('index.html', SCOPE).href;

self.addEventListener('install', event => event.waitUntil(installRelease()));
self.addEventListener('activate', event => event.waitUntil(activateRelease()));
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    if (event.request.method === 'GET' && url.origin === SCOPE.origin && url.href.startsWith(SCOPE.href)) {
        event.respondWith(fetchRelease(event.request));
    }
});
self.addEventListener('message', event => {
    if (event.data?.type === 'GET_OFFLINE_STATUS' && event.ports[0]) {
        event.waitUntil(reportOfflineStatus(event.ports[0]));
    }
});

async function installRelease() {
    if (!ASSET_URLS.has(INDEX_URL) || ASSETS.some(asset => !asset.url.startsWith(SCOPE.href) || !asset.hash)) {
        throw new Error('Invalid offline assets manifest');
    }
    const existed = await caches.has(CACHE_NAME);
    const cache = await caches.open(CACHE_NAME);
    try {
        // addAll commits the batch only when every fetch and integrity check succeeds.
        // Revalidate HTTP caches even if a previous release marked resources immutable.
        await cache.addAll(ASSETS.map(asset => new Request(asset.url, { integrity: asset.hash, cache: 'no-cache' })));
    } catch (error) {
        if (!existed) await caches.delete(CACHE_NAME);
        throw error;
    }
    // Never skipWaiting: open tabs must keep using a consistent release.
}

async function activateRelease() {
    const names = await caches.keys();
    await Promise.all(names
        .filter(name => (name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME) || name === 'pwabuilder-offline-page')
        .map(name => caches.delete(name)));
    // The first page becomes offline-capable as soon as the complete install finishes.
    await self.clients.claim();
}

async function fetchRelease(request) {
    const url = new URL(request.url);
    url.search = '';
    const navigation = request.mode === 'navigate' && !ASSET_URLS.has(url.href);
    const key = navigation ? INDEX_URL : url.href;
    const cache = await caches.open(CACHE_NAME);
    const response = (navigation || ASSET_URLS.has(key)) ? await cache.match(key) : null;
    return response || fetch(request);
}

async function reportOfflineStatus(port) {
    const cache = await caches.open(CACHE_NAME);
    const cachedUrls = new Set((await cache.keys()).map(request => request.url));
    port.postMessage({
        type: 'OFFLINE_STATUS',
        ready: ASSETS.every(asset => cachedUrls.has(asset.url)),
        version: self.assetsManifest.version,
    });
}
