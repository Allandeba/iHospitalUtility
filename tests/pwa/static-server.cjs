'use strict';
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');

const mime = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.css': 'text/css',
    '.wasm': 'application/wasm',
    '.webmanifest': 'application/manifest+json',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.ico': 'image/x-icon'
};

// Resolve on every request so lifecycle tests can switch the published release.
function createStaticServer(resolveRoot) {
    return http.createServer((req, res) => {
        const root = resolveRoot();
        let relative;
        try { relative = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); }
        catch { res.writeHead(400).end(); return; }
        let file = path.resolve(root, '.' + relative);
        if (!file.startsWith(root + path.sep) && file !== root) { res.writeHead(403).end(); return; }
        if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(root, 'index.html');
        res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
        fs.createReadStream(file).pipe(res);
    });
}

module.exports = { createStaticServer };
