const fs = require('fs');
const path = require('path');
const { DOCS_DIR } = require('./manifest-manager');

// Source assets in the skill folder
const SKILL_ASSETS_DIR = path.resolve(__dirname, '../static-assets');

function installAssets() {
    try {
        if (!fs.existsSync(SKILL_ASSETS_DIR)) {
            console.warn("Skill assets dir not found:", SKILL_ASSETS_DIR);
            return;
        }

        fs.mkdirSync(DOCS_DIR, { recursive: true });

        // Prefer symlinks so docs always use the latest skill assets without re-copying.
        // Fallback to copying if symlinks are not supported.
        ensureSymlinkOrCopy(SKILL_ASSETS_DIR, path.join(DOCS_DIR, 'assets'));

        // Keep root scripts available for convenience.
        // Note: server.js resolves the docs root from the current working directory.
        ['server.js', 'start_preview.sh', 'start_preview.bat'].forEach((filename) => {
            const src = path.join(SKILL_ASSETS_DIR, filename);
            if (!fs.existsSync(src)) return;
            ensureSymlinkOrCopy(src, path.join(DOCS_DIR, filename));
        });

        const portalTemplate = path.resolve(__dirname, '../templates/portal-index.html');
        const portalTarget = path.join(DOCS_DIR, 'index.html');
        if (!fs.existsSync(portalTarget) && fs.existsSync(portalTemplate)) {
            ensureSymlinkOrCopy(portalTemplate, portalTarget);
        }

        console.log("Docs assets ready (linked to skill assets).");

    } catch (e) {
        console.error("Asset installation failed:", e);
    }
}

function ensureSymlinkOrCopy(srcPath, destPath) {
    const srcStat = safeStat(srcPath);
    if (!srcStat) {
        console.warn("Missing source:", srcPath);
        return;
    }

    const existing = safeLstat(destPath);
    if (existing) {
        if (existing.isSymbolicLink()) {
            const linkTarget = safeReadLink(destPath);
            const resolved = linkTarget ? path.resolve(path.dirname(destPath), linkTarget) : null;
            const desired = path.resolve(srcPath);
            if (resolved === desired) return;
            fs.unlinkSync(destPath);
        } else {
            moveAside(destPath);
        }
    }

    try {
        const isDir = srcStat.isDirectory();
        const type = process.platform === 'win32'
            ? (isDir ? 'junction' : 'file')
            : (isDir ? 'dir' : 'file');

        fs.symlinkSync(srcPath, destPath, type);
        return;
    } catch (e) {
        console.warn(`Symlink failed (${destPath}). Falling back to copy.`, e.message);
    }

    // Fallback: copy
    if (srcStat.isDirectory()) {
        copyFolder(srcPath, destPath);
    } else {
        fs.copyFileSync(srcPath, destPath);
        if (destPath.endsWith('.sh')) {
            try { fs.chmodSync(destPath, '755'); } catch { }
        }
    }
}

function safeStat(p) {
    try { return fs.statSync(p); } catch { return null; }
}

function safeLstat(p) {
    try { return fs.lstatSync(p); } catch { return null; }
}

function safeReadLink(p) {
    try { return fs.readlinkSync(p); } catch { return null; }
}

function moveAside(p) {
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backup = `${p}.bak-${stamp}`;
    fs.renameSync(p, backup);
    console.log(`Moved existing path to backup: ${backup}`);
}

// Simple recursive copy helper (used only for symlink fallback)
function copyFolder(src, dest) {
    if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);
        if (entry.isDirectory()) copyFolder(srcPath, destPath);
        else fs.copyFileSync(srcPath, destPath);
    }
}


// Run if called directly
if (require.main === module) {
    installAssets();
}

module.exports = { installAssets };
