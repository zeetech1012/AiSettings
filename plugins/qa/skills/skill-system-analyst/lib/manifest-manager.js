const fs = require('fs');
const path = require('path');

const DOCS_DIR = path.resolve(process.cwd(), 'docs');
const MANIFEST_PATH = path.join(DOCS_DIR, 'manifest.json');

function ensureManifest() {
    if (!fs.existsSync(DOCS_DIR)) {
        fs.mkdirSync(DOCS_DIR, { recursive: true });
    }
    if (!fs.existsSync(MANIFEST_PATH)) {
        const initial = {
            project_name: "Project Documentation",
            last_updated: new Date().toISOString(),
            categories: ["Core Business", "Infrastructure", "Utils", "API"],
            documents: []
        };
        fs.writeFileSync(MANIFEST_PATH, JSON.stringify(initial, null, 2));
    }
}

function getManifest() {
    ensureManifest();
    try {
        return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
    } catch (e) {
        console.error("Manifest corrupted, resetting...");
        return { documents: [], categories: [] };
    }
}

function saveManifest(data) {
    data.last_updated = new Date().toISOString();
    fs.writeFileSync(MANIFEST_PATH, JSON.stringify(data, null, 2));
}

function getDocument(id) {
    const manifest = getManifest();
    return manifest.documents.find(d => d.id === id);
}

function listDocuments() {
    return getManifest().documents;
}

/**
 * Register or Update a document
 */
function upsertDocument(docPayload) {
    const manifest = getManifest();
    const idx = manifest.documents.findIndex(d => d.id === docPayload.id);

    const entry = {
        id: docPayload.id,
        title: docPayload.title,
        category: docPayload.category,
        filepath: docPayload.filepath, // relative to docs/
        summary: docPayload.summary,
        related_files: docPayload.related_files || [],
        last_updated: new Date().toISOString(),
        version: idx > -1 ? (manifest.documents[idx].version + 1) : 1
    };

    if (idx > -1) {
        manifest.documents[idx] = entry;
        console.log(`Updated manifest entry for ${entry.id} (v${entry.version})`);
    } else {
        manifest.documents.push(entry);
        console.log(`Registered new document ${entry.id}`);
    }

    // Ensure category exists
    if (!manifest.categories.includes(entry.category)) {
        manifest.categories.push(entry.category);
    }

    saveManifest(manifest);
    return entry;
}

function deleteDocument(id) {
    const manifest = getManifest();
    const idx = manifest.documents.findIndex(d => d.id === id);
    if (idx > -1) {
        manifest.documents.splice(idx, 1);
        saveManifest(manifest);
        console.log(`Removed ${id} from registry`);
        return true;
    }
    return false;
}

module.exports = {
    getManifest,
    getDocument,
    listDocuments,
    upsertDocument,
    deleteDocument,
    DOCS_DIR
};
