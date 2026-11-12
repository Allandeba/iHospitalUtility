'use strict';
// Published-release lifecycle checks; all fixture changes stay in a temporary directory.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { chromium } = require('playwright');
const root = path.resolve(process.argv[2] || '');
assert.ok(fs.existsSync(path.join(root, 'service-worker-assets.js')), 'Pass a published PWA wwwroot');
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'ihospital-pwa-lifecycle-'));
let activeRoot = root;
const mime = { '.html': 'text/html', '.js': 'application/javascript', '.json': 'application/json', '.css': 'text/css', '.wasm': 'application/wasm', '.webmanifest': 'application/manifest+json', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' };
const server = http.createServer((req, res) => {
    const base = activeRoot;
    const url = new URL(req.url, 'http://localhost');
    let file = path.resolve(base, '.' + decodeURIComponent(url.pathname));
    if (!file.startsWith(base + path.sep) && file !== base) { res.writeHead(403).end(); return; }
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(base, 'index.html');
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    fs.createReadStream(file).pipe(res);
});
function manifest(directory) {
    const self = {};
    vm.runInNewContext(fs.readFileSync(path.join(directory, 'service-worker-assets.js'), 'utf8'), { self });
    return JSON.parse(JSON.stringify(self.assetsManifest));
}
function fixture(version, corrupt = false) {
    const directory = path.join(scratch, version);
    fs.cpSync(root, directory, { recursive: true });
    const index = fs.readFileSync(path.join(directory, 'index.html'), 'utf8').replace('</body>', `<!-- ${version} -->\n</body>`);
    fs.writeFileSync(path.join(directory, 'index.html'), index);
    const data = manifest(directory);
    data.version = version;
    data.assets.find(asset => asset.url === 'index.html').hash = 'sha256-' + crypto.createHash('sha256').update(index).digest('base64');
    fs.writeFileSync(path.join(directory, 'service-worker-assets.js'), 'self.assetsManifest = ' + JSON.stringify(data) + ';\n');
    fs.appendFileSync(path.join(directory, 'pwabuilder-sw.js'), `\n// Lifecycle fixture: ${version}\n`);
    if (corrupt) fs.appendFileSync(path.join(directory, 'pwa-registration.js'), '\n// Intentional integrity mismatch, not a release file.\n');
    return directory;
}
async function until(check, message) {
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
        if (await check()) return;
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error(message);
}
async function waitForActivation(context, version) {
    await until(async () => {
        for (const worker of context.serviceWorkers()) {
            const current = await worker.evaluate(() => self.registration.active?.state === 'activated' && !self.registration.waiting && self.assetsManifest?.version).catch(() => null);
            if (current === version) return true;
        }
        return false;
    }, 'Replacement worker did not activate after closing its old pages');
}
async function update(page) {
    return page.evaluate(async () => {
        const registration = await navigator.serviceWorker.getRegistration();
        const state = new Promise((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error('Worker update timed out')), 30000);
            registration.addEventListener('updatefound', () => {
                const worker = registration.installing;
                const changed = () => {
                    if (worker.state === 'installed' || worker.state === 'redundant') {
                        clearTimeout(timer);
                        resolve(worker.state);
                    }
                };
                worker.addEventListener('statechange', changed);
                changed();
            }, { once: true });
        });
        await registration.update();
        return state;
    });
}

(async () => {
    const v1 = manifest(root).version;
    const v2 = 'lifecycle-v2';
    const release2 = fixture(v2);
    const badRelease = fixture('lifecycle-bad-v3', true);
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const origin = `http://127.0.0.1:${server.address().port}`;
    const browser = await chromium.launch({ headless: true });
    const proof = { cases: [], pageErrors: [] };
    const contexts = [];
    try {
        const context = await browser.newContext({ locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
        contexts.push(context);
        // Optional fonts/CDNs must not be required to prepare or use the application.
        await context.route(/^https:\/\//, route => route.abort());
        let page = await context.newPage();
        context.on('page', p => p.on('pageerror', e => proof.pageErrors.push(e.message)));
        page.on('pageerror', e => proof.pageErrors.push(e.message));
        await page.goto(origin + '/gestational-age', { waitUntil: 'networkidle' });
        await page.locator('#offline-status[data-offline-state="ready"]').waitFor({ timeout: 60000 });
        await page.evaluate(() => localStorage.setItem('pwa-test-preserved', 'yes'));
        await context.setOffline(true);
        await page.reload({ waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelectorAll('input').length === 4);
        proof.cases.push('first visit on a deep link, with external resources blocked, reloads offline');
        await context.setOffline(false);
        activeRoot = release2;
        assert.equal(await update(page), 'installed');
        assert.ok(await page.evaluate(async () => !!(await navigator.serviceWorker.getRegistration()).waiting));
        await page.reload({ waitUntil: 'networkidle' });
        assert.equal(await page.evaluate(() => document.documentElement.outerHTML.includes('<!-- lifecycle-v2 -->')), false);
        const waitingCaches = await page.evaluate(() => caches.keys());
        assert.ok(waitingCaches.includes('ihospitalutility-offline-' + v1));
        assert.ok(waitingCaches.includes('ihospitalutility-offline-' + v2));
        proof.cases.push('a complete update waits while old pages remain open; old shell stays consistent');
        await page.close();
        await waitForActivation(context, v2);
        await context.setOffline(true);
        page = await context.newPage();
        await page.goto(origin + '/gestational-age', { waitUntil: 'networkidle' });
        await page.locator('#offline-status[data-offline-state="ready"]').waitFor();
        assert.ok(await page.evaluate(() => document.documentElement.outerHTML.includes('<!-- lifecycle-v2 -->')));
        assert.equal(await page.evaluate(() => localStorage.getItem('pwa-test-preserved')), 'yes');
        const activeCaches = await page.evaluate(() => caches.keys());
        assert.ok(!activeCaches.includes('ihospitalutility-offline-' + v1));
        proof.cases.push('after old pages close, the new release opens offline and preserves preferences');
        await context.setOffline(false);
        activeRoot = badRelease;
        assert.equal(await update(page), 'redundant');
        const rejectedCaches = await page.evaluate(() => caches.keys());
        assert.ok(rejectedCaches.includes('ihospitalutility-offline-' + v2));
        assert.ok(!rejectedCaches.includes('ihospitalutility-offline-lifecycle-bad-v3'));
        await context.setOffline(true);
        await page.reload({ waitUntil: 'networkidle' });
        await page.locator('#offline-status[data-offline-state="ready"]').waitFor();
        assert.ok(await page.evaluate(() => document.documentElement.outerHTML.includes('<!-- lifecycle-v2 -->')));
        proof.cases.push('an actual integrity mismatch rejects the candidate and keeps the previous release offline');
        await context.close();

        activeRoot = badRelease;
        const incomplete = await browser.newContext();
        contexts.push(incomplete);
        const incompletePage = await incomplete.newPage();
        await incompletePage.goto(origin + '/', { waitUntil: 'networkidle' });
        await incompletePage.getByRole('link', { name: 'Clique para acessar', exact: true }).waitFor();
        await incompletePage.locator('#offline-status[data-offline-state="unavailable"]').waitFor({ timeout: 30000 });
        assert.equal(await incompletePage.evaluate(() => !!navigator.serviceWorker.controller), false);
        assert.ok(!(await incompletePage.evaluate(() => caches.keys())).includes('ihospitalutility-offline-lifecycle-bad-v3'));
        proof.cases.push('an incomplete first download never reports offline readiness or leaves a partial release cache');
        await incomplete.close();

        if (process.env.PWA_LEGACY_DIR) {
            activeRoot = path.resolve(process.env.PWA_LEGACY_DIR);
            const legacy = await browser.newContext({ locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
            contexts.push(legacy);
            let oldPage = await legacy.newPage();
            await oldPage.goto(origin + '/', { waitUntil: 'networkidle' });
            await oldPage.getByRole('link', { name: 'Clique para acessar', exact: true }).waitFor();
            await oldPage.evaluate(() => navigator.serviceWorker.ready);
            await oldPage.reload({ waitUntil: 'networkidle' });
            await oldPage.getByRole('link', { name: 'Clique para acessar', exact: true }).waitFor();
            assert.ok(await oldPage.evaluate(() => !!navigator.serviceWorker.controller));
            await oldPage.evaluate(() => localStorage.setItem('legacy-preference', 'preserved'));
            activeRoot = root;
            assert.equal(await update(oldPage), 'installed');
            await oldPage.close();
            await waitForActivation(legacy, v1);
            await legacy.setOffline(true);
            oldPage = await legacy.newPage();
            await oldPage.goto(origin + '/', { waitUntil: 'networkidle' });
            await oldPage.locator('#offline-status[data-offline-state="ready"]').waitFor();
            assert.equal(await oldPage.evaluate(() => localStorage.getItem('legacy-preference')), 'preserved');
            assert.ok(!(await oldPage.evaluate(() => caches.keys())).includes('pwabuilder-offline-page'));
            await oldPage.getByRole('link', { name: 'Clique para acessar', exact: true }).click();
            await oldPage.waitForFunction(() => document.querySelectorAll('input').length === 4);
            proof.cases.push('legacy Workbox worker migrates after pages close; old cache is removed and preferences survive');
            await legacy.close();
        }
        assert.deepEqual(proof.pageErrors, []);
        proof.status = 'passed';
    } catch (error) {
        proof.status = 'failed';
        proof.failure = error.stack;
        process.exitCode = 1;
    } finally {
        console.log(JSON.stringify(proof, null, 2));
        if (process.env.PWA_PROOF_DIR) {
            fs.mkdirSync(process.env.PWA_PROOF_DIR, { recursive: true });
            fs.writeFileSync(path.join(process.env.PWA_PROOF_DIR, 'lifecycle.json'), JSON.stringify(proof, null, 2));
        }
        for (const context of contexts) await context.close().catch(() => null);
        await browser.close();
        await new Promise(resolve => server.close(resolve));
        fs.rmSync(scratch, { recursive: true, force: true });
    }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
