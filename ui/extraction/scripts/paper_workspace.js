/**
 * Paper Workspace - Orquestador Principal
 * Coordina PDFViewer, QuoteManager y TagManager usando eventos
 */

class PaperWorkspace {
    constructor(config) {
        this.config = config;
        this.pdfViewer = null;
        this.quoteManager = null;
        this.tagManager = null;
        
        console.log('🚀 PaperWorkspace initialized');
    }

    async init() {
        try {
            // 1. Inicializar componentes
            this.pdfViewer = new PDFViewer(this.config);
            this.quoteManager = new QuoteManager(this.config);
            this.tagManager = new TagManager(this.config);

            // 2. Configurar event listeners globales
            this.setupEventListeners();

            // 3. Inicializar componentes
            this.quoteManager.init();
            this.tagManager.init();
            await this.pdfViewer.init();

            console.log('✅ Workspace ready');
        } catch (error) {
            console.error('❌ Init failed:', error);
        }
    }

    setupEventListeners() {
        // Selección de texto
        document.addEventListener('mouseup', (e) => {
            const selection = window.getSelection();
            const text = selection.toString().trim();
            if (text.length < 10) return;

            let pageNumber = 1;
            let node = selection.anchorNode;
            if (node && node.nodeType === 3) node = node.parentNode;
            if (node) {
                const pageContainer = node.closest('.page-container');
                if (pageContainer) {
                    pageNumber = parseInt(pageContainer.dataset.pageNumber) || 1;
                }
            }

            // Disparar evento para QuoteManager
            window.dispatchEvent(new CustomEvent('text:selected', {
                detail: { text, page: pageNumber }
            }));
        });

        // Cuando se crea una quote, actualizar PDF
        window.addEventListener('quote:created', (e) => {
            this.config.existingQuotes = this.config.existingQuotes || [];
            this.config.existingQuotes.push(e.detail.quote);
            this.pdfViewer.highlightNewQuote(e.detail.quote);
        });
    }
}

// Funciones globales
window.scrollToQuote = function(quoteId, page) {
    const pageEl = document.querySelector(`[data-page-number="${page}"]`);
    if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
};

window.deleteQuote = async function(quoteId) {
    if (!confirm('¿Eliminar esta extracción?')) return;
    
    const url = window.PAPER_CONFIG.quoteDeleteUrlTemplate.replace('{id}', quoteId);
    try {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': window.PAPER_CONFIG.csrfToken }
        });
        if (response.ok) location.reload();
        else alert('Error al eliminar');
    } catch (error) {
        alert('Error de red');
    }
};

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    if (!window.PAPER_CONFIG) {
        console.error('❌ PAPER_CONFIG not found!');
        return;
    }
    const workspace = new PaperWorkspace(window.PAPER_CONFIG);
    workspace.init();
});