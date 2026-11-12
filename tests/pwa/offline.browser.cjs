'use strict';
// Run against a published wwwroot, not the development server.
// npm ci --prefix tests/pwa && npm run browser --prefix tests/pwa -- /path/to/wwwroot
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const { createStaticServer } = require('./static-server.cjs');

const root = path.resolve(process.argv[2] || '');
assert.ok(fs.existsSync(path.join(root, 'index.html')), 'Pass a published wwwroot directory');
const server = createStaticServer(() => root);

(async () => {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const origin = process.env.PWA_BASE_URL || `http://127.0.0.1:${server.address().port}`;
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ locale: 'pt-BR', timezoneId: 'America/Sao_Paulo', viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    const proof = { origin, errors: [], cases: [] };
    page.on('pageerror', error => proof.errors.push(error.message));
    try {
        await page.goto(origin + '/', { waitUntil: 'networkidle', timeout: 60000 });
        await page.getByRole('link', { name: 'Clique para acessar', exact: true }).waitFor({ timeout: 60000 });
        await page.evaluate(() => navigator.serviceWorker.ready);
        await page.waitForFunction(() => !!navigator.serviceWorker.controller, { timeout: 3000 }).catch(() => null);
        proof.beforeOffline = await page.evaluate(async () => {
            const cacheNames = await caches.keys();
            const cached = {};
            for (const name of cacheNames) {
                const urls = (await (await caches.open(name)).keys()).map(req => new URL(req.url).pathname);
                cached[name] = { count: urls.length, corePaths: urls.filter(url => ['/', '/index.html', '/offline.html', '/_framework/blazor.boot.json'].includes(url)) };
            }
            return { controlled: !!navigator.serviceWorker.controller, cacheNames, cached };
        });
        await context.setOffline(true);
        await page.reload({ waitUntil: 'networkidle', timeout: 30000 });
        await page.getByRole('link', { name: 'Clique para acessar', exact: true }).waitFor({ timeout: 30000 });
        proof.cases.push('offline reload after first online visit');
        await page.locator('#offline-status[data-offline-state="ready"]').waitFor({ timeout: 10000 });
        proof.offlineStatus = await page.locator('#offline-status').innerText();
        await page.getByRole('link', { name: 'Clique para acessar', exact: true }).click();
        await page.waitForFunction(() => document.querySelectorAll('input').length === 4);
        for (const [i, value] of [[1, '9'], [2, '26'], [3, '1']]) {
            await page.locator('input').nth(i).fill(value);
            await page.locator('input').nth(i).press('Tab');
        }
        await page.getByRole('button', { name: 'Calcular Idade Gestacional Corrigida', exact: true }).click();
        await page.getByText('27 semanas e 3 dias', { exact: true }).waitFor();
        proof.cases.push('navigate and calculate offline without prior calculator visit');
        await page.reload({ waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelectorAll('input').length === 4);
        proof.cases.push('deep-link reload offline');
        assert.deepEqual(proof.errors, []);
        proof.status = 'passed';
    } catch (error) {
        proof.status = 'failed';
        proof.failure = error.message;
        process.exitCode = 1;
    } finally {
        if (process.env.PWA_PROOF_DIR) {
            fs.mkdirSync(process.env.PWA_PROOF_DIR, { recursive: true });
            fs.writeFileSync(path.join(process.env.PWA_PROOF_DIR, 'browser.json'), JSON.stringify(proof, null, 2));
            await page.screenshot({ path: path.join(process.env.PWA_PROOF_DIR, 'offline.png'), fullPage: true }).catch(() => null);
        }
        console.log(JSON.stringify(proof, null, 2));
        await context.close();
        await browser.close();
        await new Promise(resolve => server.close(resolve));
    }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
