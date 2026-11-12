'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

test('shared browser test server preserves published-release serving', async t => {
    const helper = path.join(__dirname, 'static-server.cjs');
    assert.ok(fs.existsSync(helper), 'The browser scenarios need a shared static server helper');
    const { createStaticServer } = require(helper);
    const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'ihospital-static-test-'));
    const release1 = path.join(scratch, 'release1');
    const release2 = path.join(scratch, 'release2');
    for (const root of [release1, release2]) fs.mkdirSync(root);
    fs.mkdirSync(path.join(release1, 'directory'));
    fs.writeFileSync(path.join(release1, 'index.html'), '<main>release one</main>');
    fs.writeFileSync(path.join(release2, 'index.html'), '<main>release two</main>');
    fs.writeFileSync(path.join(scratch, 'outside.txt'), 'not a published asset');
    let activeRoot = release1;
    const server = createStaticServer(() => activeRoot);
    t.after(async () => {
        await new Promise(resolve => server.close(resolve));
        fs.rmSync(scratch, { recursive: true, force: true });
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const origin = `http://127.0.0.1:${server.address().port}`;

    await t.test('published assets retain MIME types, query handling and no-cache headers', async () => {
        const types = {
            '.js': 'application/javascript', '.json': 'application/json', '.css': 'text/css',
            '.wasm': 'application/wasm', '.webmanifest': 'application/manifest+json',
            '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon',
            '.woff2': 'application/octet-stream'
        };
        for (const [extension, type] of Object.entries(types)) {
            const asset = 'asset' + extension;
            fs.writeFileSync(path.join(release1, asset), 'fixture ' + extension);
            const response = await fetch(origin + '/' + asset + '?v=1');
            assert.equal(response.status, 200);
            assert.equal(response.headers.get('content-type'), type);
            assert.equal(response.headers.get('cache-control'), 'no-cache');
            assert.equal(await response.text(), 'fixture ' + extension);
        }
    });

    await t.test('home, directory and deep-link requests retain the SPA shell fallback', async () => {
        for (const route of ['/', '/directory/', '/gestational-age?source=test']) {
            const response = await fetch(origin + route);
            assert.equal(response.status, 200);
            assert.equal(response.headers.get('content-type'), 'text/html');
            assert.equal(await response.text(), '<main>release one</main>');
        }
    });

    await t.test('malformed URL encoding is rejected without stopping the server', async () => {
        const response = await fetch(origin + '/%E0%A4%A');
        assert.equal(response.status, 400);
        await response.text();
        assert.equal((await fetch(origin + '/')).status, 200);
    });

    await t.test('encoded traversal cannot expose files outside the active release', async () => {
        const response = await fetch(origin + '/..%2Foutside.txt');
        assert.equal(response.status, 403);
        assert.equal(await response.text(), '');
    });

    await t.test('the next request uses the new root when the active release changes', async () => {
        activeRoot = release2;
        const response = await fetch(origin + '/');
        assert.equal(response.status, 200);
        assert.equal(await response.text(), '<main>release two</main>');
    });
});
