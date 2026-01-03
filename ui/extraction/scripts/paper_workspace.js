// ui/extraction/static/scripts/paper_workspace.js

/**
 * Paper Workspace - Orquestador Principal
 * Coordina los componentes: PDFViewer, TagManager, QuoteManager
 */

console.log('🟢 paper_workspace.js loaded');

// Importar módulos (simulado, ya que no usamos ES6 modules)
// En producción considera usar webpack o vite

const CONFIG = window.WORKSPACE_CONFIG || {};

// Validar configuración
if (!CONFIG.pdfUrl || !CONFIG.apiUrl || !CONFIG.csrfToken) {
    console.error('❌ CRITICAL: Incomplete configuration');
    alert('Error de configuración. Recarga la página.');
    throw new Error('Missing WORKSPACE_CONFIG');
}

console.log('✅ Configuration loaded');

// ========================================
// INICIALIZACIÓN DE COMPONENTES
// ========================================

let pdfViewer = null;
let tagManager = null;
let quoteManager = null;

// ui/extraction/static/scripts/paper_workspace.js

async function initWorkspace() {
    console.log('🚀 Initializing workspace...');

    try {
        // 1. Inicializar Tag Manager (síncrono)
        tagManager = new TagManager({
            containerSelector: '#tags-container',
            searchInputSelector: '#tag-search-input'
        });
        tagManager.init();

        // 2. Inicializar Quote Manager INMEDIATAMENTE
        quoteManager = new QuoteManager({
            apiUrl: CONFIG.apiUrl,
            deleteApiUrl: CONFIG.deleteApiUrl,
            csrfToken: CONFIG.csrfToken,
            paperId: CONFIG.paperId,
            pdfViewer: null,  // ⬅️ null temporalmente
            tagManager: tagManager
        });
        quoteManager.init();

        console.log('📊 CONFIG.existingQuotes:', CONFIG.existingQuotes);
        console.log('📊 Type:', typeof CONFIG.existingQuotes);
        console.log('📊 Is Array:', Array.isArray(CONFIG.existingQuotes));
        console.log('📊 Length:', CONFIG.existingQuotes?.length);

        // 3. Inicializar PDF Viewer (asíncrono, SIN await)
        pdfViewer = new PDFViewer({
            containerSelector: '#pdf-viewer-container',
            loaderSelector: '#pdf-loader',
            pdfUrl: CONFIG.pdfUrl,
            existingQuotes: CONFIG.existingQuotes,
            onSelectionChange: (selection) => {  // ✅ NUEVO: Callback directo
                quoteManager.handleTextSelection(selection);
            }
        });

        // ✅ NO usar await - dejamos que cargue en paralelo
        pdfViewer.init().then(() => {
            console.log('✅ PDF Viewer fully loaded');

            // ✅ Conectar pdfViewer con quoteManager después de cargar
            quoteManager.pdfViewer = pdfViewer;
        }).catch((error) => {
            console.error('❌ Error loading PDF:', error);
        });

        console.log('✅ Workspace initialized (PDF loading in background)');

    } catch (error) {
        console.error('❌ Error initializing workspace:', error);
    }
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWorkspace);
} else {
    initWorkspace();
}