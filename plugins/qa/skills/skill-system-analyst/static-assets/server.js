const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const PORT = 8085;
const DOCS_ROOT = resolveDocsRoot();

const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml'
};

function resolveDocsRoot() {
    const cwd = process.cwd();
    const candidate = path.join(cwd, 'docs');
    if (fs.existsSync(candidate)) {
        try {
            if (fs.statSync(candidate).isDirectory()) {
                return candidate;
            }
        } catch { }
    }
    return cwd;
}

const server = http.createServer((req, res) => {
    console.log(`${req.method} ${req.url}`);

    const requestUrl = new URL(req.url, `http://localhost:${PORT}`);
    const pathname = decodeURIComponent(requestUrl.pathname || '/');

    const relativePath = (pathname === '/' ? 'index.html' : pathname).replace(/^\/+/, '');

    // Normalized path
    let filePath = path.join(DOCS_ROOT, relativePath);

    // Prevent directory traversal
    if (!filePath.startsWith(DOCS_ROOT)) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
    }

    const ext = path.extname(filePath);
    let contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404);
                res.end('Not Found');
            } else {
                res.writeHead(500);
                res.end(`Server Error: ${err.code}`);
            }
        } else {
            res.writeHead(200, {
                'Content-Type': contentType,
                // Avoid stale assets when iterating on the skill’s JS/CSS.
                'Cache-Control': 'no-store, max-age=0',
                'Pragma': 'no-cache',
                'Expires': '0'
            });
            res.end(content, 'utf-8');
        }
    });
});

server.listen(PORT, () => {
    const url = `http://localhost:${PORT}`;
    console.log(`\n📚 Documentation Portal running at: ${url}`);
    console.log('Press Ctrl+C to stop.\n');

    // Auto-open browser
    const startCmd = process.platform === 'darwin' ? 'open' :
        process.platform === 'win32' ? 'start' : 'xdg-open';

    exec(`${startCmd} ${url}`);
});
