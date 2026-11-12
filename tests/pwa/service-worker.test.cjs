'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.resolve(__dirname, '../../src/iHospitalUtility/wwwroot/pwabuilder-sw.published.js'), 'utf8');
const origin = 'https://app.example/';
const prefix = 'ihospitalutility-offline-';
const assets = [
    { url: 'index.html', hash: 'sha256-index' },
    { url: '_framework/app.wasm', hash: 'sha256-wasm' },
    { url: 'pwa-registration.js', hash: 'sha256-js' },
];

function worker({ version = 'v1', manifestAssets = assets, failInstall = false, existing = {} } = {}) {
    const listeners = {};
    const stores = new Map(Object.entries(existing).map(([name, entries]) => [name, new Map(Object.entries(entries))]));
    const state = { imports: [], added: [], deleted: [], claimed: 0, skipped: 0, network: [] };
    const caches = {
        async has(name) { return stores.has(name); },
        async keys() { return [...stores.keys()]; },
        async delete(name) { state.deleted.push(name); return stores.delete(name); },
        async open(name) {
            if (!stores.has(name)) stores.set(name, new Map());
            const store = stores.get(name);
            return {
                async addAll(requests) {
                    state.added = requests;
                    if (failInstall) throw new Error('asset integrity or network failure');
                    for (const request of requests) store.set(request.url, new Response(request.url.endsWith('index.html') ? 'shell-' + version : 'asset'));
                },
                async match(key) { return store.get(typeof key === 'string' ? key : key.url)?.clone(); },
                async keys() { return [...store.keys()].map(url => new Request(url)); },
            };
        },
    };
    const self = {
        assetsManifest: { version, assets: manifestAssets },
        location: new URL(origin + 'pwabuilder-sw.js'),
        registration: { scope: origin },
        importScripts(url) { state.imports.push(url); },
        addEventListener(name, listener) { assert.ok(!listeners[name], 'only one listener per event'); listeners[name] = listener; },
        clients: { async claim() { state.claimed++; } },
        skipWaiting() { state.skipped++; },
    };
    vm.runInNewContext(source, {
        self, caches, URL, Request, Response, console,
        async fetch(request) { state.network.push(request.url); return new Response('network'); },
    });
    function dispatch(name, props = {}) {
        let promise;
        listeners[name]({ ...props, waitUntil(value) { promise = value; }, respondWith(value) { promise = value; } });
        return promise;
    }
    return { state, stores, dispatch };
}

test('offline worker depends only on the local generated assets manifest', () => {
    assert.deepEqual(worker().state.imports, ['./service-worker-assets.js']);
});

test('installation precaches every manifest asset with integrity and HTTP revalidation', async () => {
    const w = worker();
    await w.dispatch('install');
    assert.deepEqual(Array.from(w.state.added, r => r.url), assets.map(a => new URL(a.url, origin).href));
    assert.deepEqual(Array.from(w.state.added, r => r.integrity), assets.map(a => a.hash));
    assert.ok(w.state.added.every(r => r.cache === 'no-cache'));
    assert.equal(w.state.claimed, 0);
    assert.equal(w.state.skipped, 0);
});

test('incomplete installation is rejected without deleting the previous release', async () => {
    const w = worker({ failInstall: true, existing: { [prefix + 'previous']: { [origin + 'index.html']: new Response('old') } } });
    await assert.rejects(w.dispatch('install'), /asset integrity or network failure/);
    assert.ok(w.stores.has(prefix + 'previous'));
    assert.ok(!w.stores.has(prefix + 'v1'));
    assert.equal(w.state.claimed, 0);
});

test('failed reinstall never deletes an already active cache of the same version', async () => {
    const w = worker({ failInstall: true, existing: { [prefix + 'v1']: { [origin + 'index.html']: new Response('old') } } });
    await assert.rejects(w.dispatch('install'), /asset integrity or network failure/);
    assert.ok(w.stores.has(prefix + 'v1'));
    assert.equal(await w.stores.get(prefix + 'v1').get(origin + 'index.html').text(), 'old');
    assert.deepEqual(w.state.deleted, []);
});

test('activation cleans only obsolete application caches and claims the first page', async () => {
    const w = worker({ existing: { [prefix + 'old']: {}, 'pwabuilder-offline-page': {}, 'another-app-cache': {}, 'dotnet-resources-/': {} } });
    await w.dispatch('install');
    await w.dispatch('activate');
    assert.deepEqual(w.state.deleted.sort(), [prefix + 'old', 'pwabuilder-offline-page'].sort());
    assert.ok(w.stores.has(prefix + 'v1') && w.stores.has('another-app-cache') && w.stores.has('dotnet-resources-/'));
    assert.equal(w.state.claimed, 1);
    assert.equal(w.state.skipped, 0);
});

test('offline deep links and query strings receive the cached application shell', async () => {
    const w = worker();
    await w.dispatch('install');
    const response = await w.dispatch('fetch', { request: { method: 'GET', mode: 'navigate', url: origin + 'gestational-age?source=shortcut' } });
    assert.equal(await response.text(), 'shell-v1');
    assert.deepEqual(w.state.network, []);
});

test('known resources use their versioned cache even with a cache-busting query', async () => {
    const w = worker();
    await w.dispatch('install');
    const response = await w.dispatch('fetch', { request: { method: 'GET', mode: 'cors', url: origin + '_framework/app.wasm?v=1' } });
    assert.equal(await response.text(), 'asset');
    assert.deepEqual(w.state.network, []);
});

test('non-GET and cross-origin requests are not intercepted or cached', () => {
    const w = worker();
    assert.equal(w.dispatch('fetch', { request: { method: 'POST', url: origin + 'api/save' } }), undefined);
    assert.equal(w.dispatch('fetch', { request: { method: 'GET', url: 'https://other.example/app.js' } }), undefined);
    assert.deepEqual(w.state.network, []);
});

test('unknown non-navigation resources fall through to network and are never cached', async () => {
    const w = worker();
    await w.dispatch('install');
    const request = { method: 'GET', mode: 'cors', url: origin + 'future-api?data=private' };
    assert.equal(await (await w.dispatch('fetch', { request })).text(), 'network');
    assert.deepEqual(w.state.network, [request.url]);
    assert.ok(!w.stores.get(prefix + 'v1').has(request.url));
});

test('readiness is reported only for a complete cache', async () => {
    const w = worker();
    const messages = [];
    const query = () => w.dispatch('message', { data: { type: 'GET_OFFLINE_STATUS' }, ports: [{ postMessage(message) { messages.push(JSON.parse(JSON.stringify(message))); } }] });
    await query();
    assert.equal(messages.at(-1).ready, false);
    await w.dispatch('install');
    await query();
    assert.deepEqual(messages.at(-1), { type: 'OFFLINE_STATUS', ready: true, version: 'v1' });
    w.stores.get(prefix + 'v1').delete(origin + '_framework/app.wasm');
    await query();
    assert.equal(messages.at(-1).ready, false);
});

test('a manifest without the application shell fails closed', async () => {
    const w = worker({ manifestAssets: assets.slice(1) });
    await assert.rejects(w.dispatch('install'), /Invalid offline assets manifest/);
    assert.equal(w.stores.size, 0);
});

test('a manifest with external resources fails closed before fetching', async () => {
    const w = worker({ manifestAssets: [...assets, { url: 'https://other.example/payload.js', hash: 'sha256-external' }] });
    await assert.rejects(w.dispatch('install'), /Invalid offline assets manifest/);
    assert.equal(w.stores.size, 0);
});
