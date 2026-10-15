const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const { getManifest, upsertDocument, DOCS_DIR } = require('./manifest-manager');
const { installAssets } = require('./setup');

const TEMPLATE_PATH = path.resolve(__dirname, '../templates/doc-shell.html');
const SESSION_DIR = path.join(__dirname, '../sessions');

// Ensure session directory exists
if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
}

function checkAndStartServer() {
    return new Promise((resolve) => {
        const port = 8085;
        const socket = new net.Socket();

        const startServer = () => {
            console.log("Starting preview server on port 8085...");
            const serverScript = path.join(DOCS_DIR, 'server.js');

            const child = spawn('node', [serverScript], {
                detached: true,
                stdio: 'ignore'
            });
            child.unref();
            resolve(true);
        };

        socket.setTimeout(200);
        socket.on('connect', () => {
            socket.destroy();
            resolve(false);
        });

        socket.on('timeout', () => {
            socket.destroy();
            startServer();
        });

        socket.on('error', (err) => {
            if (err.code === 'ECONNREFUSED') {
                startServer();
            } else {
                resolve(false);
            }
        });

        socket.connect(port, '127.0.0.1');
    });
}

// --- Commands ---

function generateSessionId() {
    return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
}

/**
 * INIT: Create a new document session
 */
function cmdInit(metadataPath) {
    try {
        const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
        const sessionId = generateSessionId();
        const sessionFile = path.join(SESSION_DIR, `${sessionId}.json`);

        const sessionData = {
            id: metadata.id,
            title: metadata.title,
            category: metadata.category,
            summary: metadata.summary,
            related_files: metadata.related_files || [],
            mindmap_markdown: metadata.mindmap_markdown || '',
            sections: [],
            created_at: new Date().toISOString()
        };

        fs.writeFileSync(sessionFile, JSON.stringify(sessionData, null, 2));
        console.log(`Session initialized. ID: ${sessionId}`);
        return sessionId;
    } catch (e) {
        console.error("Init failed:", e.message);
        process.exit(1);
    }
}

/**
 * APPEND: Add a section to the document
 */
function cmdAppend(sessionId, sectionPath) {
    try {
        const sessionFile = path.join(SESSION_DIR, `${sessionId}.json`);
        if (!fs.existsSync(sessionFile)) throw new Error(`Session ${sessionId} not found`);

        const sessionData = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
        const sectionData = JSON.parse(fs.readFileSync(sectionPath, 'utf8'));

        // Validate section
        if (!sectionData.heading || !sectionData.content) {
            throw new Error("Invalid section format. Must have 'heading' and 'content'.");
        }

        sessionData.sections.push(sectionData);

        fs.writeFileSync(sessionFile, JSON.stringify(sessionData, null, 2));
        console.log(`Section appended to ${sessionId}. Total sections: ${sessionData.sections.length}`);
    } catch (e) {
        console.error("Append failed:", e.message);
        process.exit(1);
    }
}

/**
 * RENDER: Finalize and generate HTML
 */
async function cmdRender(sessionId) {
    try {
        const sessionFile = path.join(SESSION_DIR, `${sessionId}.json`);
        if (!fs.existsSync(sessionFile)) throw new Error(`Session ${sessionId} not found`);

        const sessionData = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));

        // 1. Combine Content
        let fullHtml = "";
        sessionData.sections.forEach(sec => {
            fullHtml += `<section><h2>${sec.heading}</h2>${sec.content}</section>\n`;
        });

        // 2. Reuse existing createDocument logic
        await createDocument({
            id: sessionData.id,
            title: sessionData.title,
            category: sessionData.category,
            summary: sessionData.summary,
            related_files: sessionData.related_files,
            mindmap_markdown: sessionData.mindmap_markdown,
            content_html: fullHtml
        });

        // 3. Cleanup
        fs.unlinkSync(sessionFile);
        console.log(`Session ${sessionId} completed and removed.`);

    } catch (e) {
        console.error("Render failed:", e.message);
        process.exit(1);
    }
}

/**
 * Core Generation Logic (Preserved)
 */
async function createDocument(params) {
    installAssets();
    await checkAndStartServer();

    const safeCategory = params.category.toLowerCase().replace(/\s+/g, '-');
    const filename = `${params.id}.html`;
    const relativePath = path.join(safeCategory, filename);
    const fullPath = path.join(DOCS_DIR, relativePath);

    const targetDir = path.dirname(fullPath);
    if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });

    upsertDocument({
        id: params.id,
        title: params.title,
        category: params.category,
        filepath: relativePath,
        summary: params.summary,
        related_files: params.related_files
    });

    const manifest = getManifest();
    let template = fs.readFileSync(TEMPLATE_PATH, 'utf8');

    template = template.replace(/{{title}}/g, params.title);
    template = template.replace(/{{doc_id}}/g, params.id);
    template = template.replace(/{{last_updated}}/g, new Date().toISOString().split('T')[0]);
    template = template.replace(/{{content}}/g, params.content_html);
    template = template.replace(/{{mindmap_data}}/g, params.mindmap_markdown);

    fs.writeFileSync(fullPath, template);
    console.log(`Document generated at: ${fullPath}`);
    return fullPath;
}

// CLI Routing
if (require.main === module) {
    const args = process.argv.slice(2);
    const command = args[0];

    if (command === 'init' && args[1]) {
        cmdInit(args[1]);
    } else if (command === 'append' && args[1] && args[2]) {
        cmdAppend(args[1], args[2]);
    } else if (command === 'render' && args[1]) {
        cmdRender(args[1]);
    } else if (args.length === 1 && command.endsWith('.json')) {
        // Fallback for backward compatibility (Single-shot mode)
        try {
            const raw = fs.readFileSync(command, 'utf8');
            const data = JSON.parse(raw);
            createDocument(data);
        } catch (e) {
            console.error("Legacy mode failed:", e.message);
        }
    } else {
        console.log(`
Usage:
  init <metadata.json>           -> returns session_id
  append <session_id> <sec.json> -> adds content
  render <session_id>            -> generates html
  <file.json>                    -> legacy single-shot mode
        `);
    }
}

module.exports = { createDocument };
