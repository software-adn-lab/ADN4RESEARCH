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

async function initWorkspace() {
    console.log('🚀 Initializing workspace...');

    try {
        // 1. Inicializar PDF Viewer
        pdfViewer = new PDFViewer({
            containerSelector: '#pdf-viewer-container',
            loaderSelector: '#pdf-loader',
            pdfUrl: CONFIG.pdfUrl,
            existingQuotes: CONFIG.existingQuotes
        });
        
        await pdfViewer.init();
        
        // 2. Inicializar Tag Manager
        tagManager = new TagManager({
            containerSelector: '#tags-container',
            searchInputSelector: '#tag-search-input'
        });
        
        tagManager.init();
        
        // 3. Inicializar Quote Manager
        quoteManager = new QuoteManager({
            apiUrl: CONFIG.apiUrl,
            csrfToken: CONFIG.csrfToken,
            paperId: CONFIG.paperId,
            pdfViewer: pdfViewer,
            tagManager: tagManager
        });
        
        quoteManager.init();
        
        console.log('✅ Workspace initialized successfully');
        
    } catch (error) {
        console.error('❌ Error initializing workspace:', error);
    }
}

// Arrancar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWorkspace);
} else {
    initWorkspace();
}