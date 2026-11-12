// Development builds intentionally do not cache application files.
// dotnet publish replaces this file with pwabuilder-sw.published.js.
self.addEventListener('fetch', () => {});
self.addEventListener('message', event => {
    if (event.data?.type === 'GET_OFFLINE_STATUS') {
        event.ports[0]?.postMessage({ type: 'OFFLINE_STATUS', ready: false, development: true });
    }
});
