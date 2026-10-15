/**
 * doc-engine.js
 * 
 * Powered by:
 * - Markmap (for System Map)
 * - Mermaid (for Diagrams)
 */

let systemMapInstance = null;
let modalMapInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    ensureDashboardButton();
    ensureMarkmapTheme();

    // 1. Show Loading State
    const mapContainer = document.querySelector('.system-map-container');
    if (mapContainer) {
        // Keep the mindmap container consistent with the dark docs theme.
        mapContainer.style.background = 'var(--card-bg)';
    }

    // 2. Wait for Libs
    let attempts = 0;
    const checkLibs = setInterval(() => {
        attempts++;
        const hasMarkmap = window.markmap && window.d3;
        const hasMermaid = window.mermaid;

        if (hasMarkmap && hasMermaid) {
            clearInterval(checkLibs);
            console.log("Libs loaded. Initializing visualizations...");
            initSystemMap();
            initMermaid();
        } else if (attempts > 50) { // 5 seconds
            clearInterval(checkLibs);
            console.error("Libs failed to load.", {
                markmap: !!window.markmap,
                d3: !!window.d3,
                mermaid: !!window.mermaid
            });
            if (!hasMarkmap) displayError('#system-map', 'Markmap libraries failed to load (check local asset paths).');
            if (!hasMermaid) document.querySelectorAll('.mermaid').forEach(el => displayError(el, 'Mermaid library failed to load.'));
        }
    }, 100);
});

function displayError(selectorOrEl, msg) {
    const el = typeof selectorOrEl === 'string' ? document.querySelector(selectorOrEl) : selectorOrEl;
    if (el) {
        const err = document.createElement('div');
        err.style.color = 'red';
        err.style.padding = '10px';
        err.style.border = '1px solid red';
        err.style.background = '#fee';
        err.innerText = '可视化渲染失败: ' + msg;
        el.replaceWith(err);
    }
}

function ensureDashboardButton() {
    // Only inject on document pages (dashboard pages don't have this meta).
    if (!document.querySelector('meta[name="doc-id"]')) return;

    const header = document.querySelector('main.main-content > header');
    if (!header) return;

    if (header.querySelector('.header-actions')) return;

    const actions = document.createElement('div');
    actions.className = 'header-actions';
    actions.innerHTML = `<a class="btn btn-secondary" href="../index.html">← Dashboard</a>`;
    header.insertBefore(actions, header.firstChild);
}

function ensureMarkmapTheme() {
    // markmap-view injects a dark theme selector: `.markmap-dark .markmap { ... }`
    // Our docs theme is dark, so enable it globally for better contrast.
    document.documentElement.classList.add('markmap-dark');
}

function initSystemMap() {
    const svg = document.querySelector('#system-map');
    const dataContainer = document.querySelector('#system-map-data');

    if (!svg || !dataContainer) return;

    const markdown = dataContainer.textContent.trim();
    if (!markdown) {
        displayError(svg, 'No Mindmap data found.');
        return;
    }

    try {
        systemMapInstance = renderMarkmap(svg, markdown);
        applySoftPanBounds(systemMapInstance);

        // Ensure layout stays correct when fonts (e.g. KaTeX) finish loading.
        if (document.fonts?.ready && window.markmap?.refreshHook) {
            document.fonts.ready
                .then(() => window.markmap.refreshHook.call())
                .catch(() => { });
        }
        console.log("Markmap rendered.");

        initSystemMapModal(markdown);
    } catch (e) {
        console.error("Markmap render error:", e);
        displayError(svg, e.message);
    }
}

function renderMarkmap(svgEl, markdown) {
    const { Transformer, Markmap } = window.markmap;

    // Defensive check
    if (!Transformer || !Markmap) {
        throw new Error(`Markmap API incomplete. Transformer: ${!!Transformer}, Markmap: ${!!Markmap}`);
    }

    applyMarkmapOverrides(svgEl);

    const transformer = new Transformer();
    const { root } = transformer.transform(markdown);
    return Markmap.create(svgEl, null, root);
}

function applyMarkmapOverrides(svgEl) {
    if (!svgEl?.style?.setProperty) return;

    // Wrap long labels so the system map doesn't become ultra-wide and unreadable.
    const isModal = svgEl.id === 'system-map-modal-svg';
    svgEl.style.setProperty('--markmap-max-width', isModal ? '420px' : '320px');

    // Improve readability on dark background (default markmap font is very light).
    svgEl.style.setProperty('--markmap-font', '500 16px/22px var(--font-sans)');
    svgEl.style.setProperty('--markmap-text-color', 'var(--text-primary)');
    svgEl.style.setProperty('--markmap-code-bg', 'rgba(255, 255, 255, 0.08)');
    svgEl.style.setProperty('--markmap-code-color', 'var(--text-primary)');
    svgEl.style.setProperty('--markmap-a-color', '#60a5fa');
    svgEl.style.setProperty('--markmap-a-hover-color', '#93c5fd');
    svgEl.style.setProperty('--markmap-circle-open-bg', 'rgba(255, 255, 255, 0.35)');
    svgEl.style.setProperty('--markmap-highlight-node-bg', 'rgba(59, 130, 246, 0.14)');
}

function applySoftPanBounds(map) {
    if (!map?.zoom || !map?.g || !window?.d3?.zoomIdentity) return;

    const baseConstrain = map.zoom.constrain();
    map.zoom.constrain((transform, extent, translateExtent) => {
        const constrained = typeof baseConstrain === 'function'
            ? baseConstrain(transform, extent, translateExtent)
            : transform;

        return clampTransform(constrained, extent, map);
    });
}

function clampTransform(transform, extent, map) {
    if (!extent || !map?.g?.node?.() || !window?.d3?.zoomIdentity) return transform;

    const [[x0, y0], [x1, y1]] = extent;
    const viewW = x1 - x0;
    const viewH = y1 - y0;

    // Soft boundary: allow some "overscroll", but make it hard to lose the mindmap entirely.
    const minDim = Math.min(viewW, viewH);
    const margin = Math.min(160, Math.max(48, Math.floor(minDim * 0.12)));

    let bbox;
    try {
        bbox = map.g.node().getBBox();
    } catch {
        return transform;
    }

    if (!bbox || !isFinite(bbox.x) || !isFinite(bbox.y) || !isFinite(bbox.width) || !isFinite(bbox.height)) {
        return transform;
    }

    const k = transform.k;
    let tx = transform.x;
    let ty = transform.y;

    const left = bbox.x * k + tx;
    const right = (bbox.x + bbox.width) * k + tx;
    const top = bbox.y * k + ty;
    const bottom = (bbox.y + bbox.height) * k + ty;

    const minX = x0 + margin;
    const maxX = x1 - margin;
    if (right < minX) tx += (minX - right);
    if (left > maxX) tx += (maxX - left);

    const minY = y0 + margin;
    const maxY = y1 - margin;
    if (bottom < minY) ty += (minY - bottom);
    if (top > maxY) ty += (maxY - top);

    if (tx === transform.x && ty === transform.y) return transform;
    return window.d3.zoomIdentity.translate(tx, ty).scale(k);
}

function initSystemMapModal(markdown) {
    const expandBtn = ensureSystemMapExpandButton();
    const { modal, modalSvg, closeBtn, fitBtn, backdrop } = ensureSystemMapModalElements();

    if (!expandBtn || !modal || !modalSvg) return;

    const open = () => {
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');

        // Delay creation until the modal is visible so the SVG has correct dimensions.
        window.requestAnimationFrame(() => {
            if (!modalMapInstance) {
                modalMapInstance = renderMarkmap(modalSvg, markdown);
                applySoftPanBounds(modalMapInstance);
            }
            if (typeof modalMapInstance?.fit === 'function') {
                modalMapInstance.fit().catch(() => { });
            }
        });
    };

    const close = () => {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('modal-open');
    };

    expandBtn.addEventListener('click', open);

    closeBtn?.addEventListener('click', close);
    fitBtn?.addEventListener('click', () => {
        if (typeof modalMapInstance?.fit === 'function') {
            modalMapInstance.fit().catch(() => { });
        }
    });

    backdrop?.addEventListener('click', close);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('is-open')) {
            close();
        }
    });
}

function ensureSystemMapExpandButton() {
    const mapContainer = document.querySelector('.system-map-container');
    if (!mapContainer) return null;

    let actions = mapContainer.querySelector('.system-map-actions');
    if (!actions) {
        actions = document.createElement('div');
        actions.className = 'system-map-actions';
        mapContainer.appendChild(actions);
    }

    let expandBtn = document.getElementById('system-map-expand');
    if (!expandBtn) {
        expandBtn = document.createElement('button');
        expandBtn.type = 'button';
        expandBtn.id = 'system-map-expand';
        expandBtn.className = 'system-map-btn';
        expandBtn.textContent = 'Open';
        actions.appendChild(expandBtn);
    }

    return expandBtn;
}

function ensureSystemMapModalElements() {
    let modal = document.getElementById('system-map-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'system-map-modal';
        modal.className = 'modal';
        modal.setAttribute('aria-hidden', 'true');
        modal.innerHTML = `
            <div class="modal-backdrop" data-action="close"></div>
            <div class="modal-dialog" role="dialog" aria-modal="true" aria-label="System Model">
                <div class="modal-titlebar">
                    <div class="modal-title">System Model</div>
                    <div class="modal-titlebar-actions">
                        <button type="button" class="btn btn-secondary" id="system-map-modal-fit">Fit</button>
                        <button type="button" class="btn btn-secondary" id="system-map-modal-close">Close</button>
                    </div>
                </div>
                <div class="modal-body">
                    <svg id="system-map-modal-svg" class="markmap"></svg>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    const modalSvg = modal.querySelector('#system-map-modal-svg');
    const closeBtn = modal.querySelector('#system-map-modal-close');
    const fitBtn = modal.querySelector('#system-map-modal-fit');
    const backdrop = modal.querySelector('.modal-backdrop');

    return { modal, modalSvg, closeBtn, fitBtn, backdrop };
}

function initMermaid() {
    try {
        window.mermaid.initialize({
            startOnLoad: true,
            theme: 'default', // 'dark' sometimes causes contrast issues if css is not perfect
            securityLevel: 'loose',
            fontFamily: 'Inter, sans-serif'
        });
        window.mermaid.run(); // Explicitly run for v10+
        console.log("Mermaid initialized.");
    } catch (e) {
        console.error("Mermaid error:", e);
    }
}
