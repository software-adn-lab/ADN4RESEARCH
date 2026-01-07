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
        // ============================================
        // 1. Selección de texto en PDF
        // ============================================
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

        // ============================================
        // 2. Cuando se crea una quote, actualizar PDF
        // ============================================
        window.addEventListener('quote:created', (e) => {
            this.config.existingQuotes = this.config.existingQuotes || [];
            this.config.existingQuotes.push(e.detail.quote);
            this.pdfViewer.highlightNewQuote(e.detail.quote);
        });

        // ============================================
        // 3. Botón de completar paper
        // ============================================
        const completeBtn = document.getElementById('complete-paper-btn');
        if (completeBtn) {
            completeBtn.addEventListener('click', this.handleCompletePaper.bind(this));
            console.log('✅ Complete button listener attached');
        } else {
            console.log('ℹ️ Complete button not found (paper may be already completed)');
        }
    }

    /**
     * Maneja la finalización del paper
     * Método de instancia para mejor encapsulación
     */
    async handleCompletePaper() {
        const btn = document.getElementById('complete-paper-btn');
        
        if (!btn) {
            console.error('Complete button not found');
            return;
        }
        
        // Confirmación
        const confirmed = confirm(
            '¿Estás seguro de que deseas finalizar la extracción de este paper?\n\n' +
            'Verifica que:\n' +
            '• Hayas extraído todas las citas relevantes\n' +
            '• Todos los tags obligatorios estén cubiertos\n\n' +
            'Esta acción marcará el paper como completado.'
        );
        
        if (!confirmed) return;
        
        // Deshabilitar botón y mostrar loading
        btn.disabled = true;
        btn.innerHTML = `
            <span class="loading loading-spinner loading-sm"></span>
            Finalizando...
        `;
        
        try {
            const response = await fetch(this.config.paperCompleteUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Mostrar toast de éxito
                showToast(data.message, 'success');
                
                // Recargar después de 1 segundo
                setTimeout(() => {
                    location.reload();
                }, 1000);
                
            } else {
                // Mostrar error
                showToast(data.error || 'Error al completar el paper', 'error');
                this.resetCompleteButton(btn);
            }
            
        } catch (error) {
            console.error('Error al completar paper:', error);
            showToast('Error de conexión', 'error');
            this.resetCompleteButton(btn);
        }
    }

    /**
     * Restaura el estado original del botón de completar
     * @param {HTMLElement} btn - Botón a restaurar
     */
    resetCompleteButton(btn) {
        btn.disabled = false;
        btn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Finalizar Extracción
        `;
    }
}

// ============================================
// Funciones Globales (Legacy Support)
// ============================================

/**
 * Scroll a una quote específica en el PDF
 * @param {number} quoteId - ID de la quote
 * @param {number} page - Número de página
 */
window.scrollToQuote = function(quoteId, page) {
    const pageEl = document.querySelector(`[data-page-number="${page}"]`);
    if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
};

/**
 * Elimina una quote
 * @param {number} quoteId - ID de la quote a eliminar
 */
window.deleteQuote = async function(quoteId) {
    if (!confirm('¿Eliminar esta extracción?')) return;
    
    const url = window.PAPER_CONFIG.quoteDeleteUrlTemplate.replace('{id}', quoteId);
    try {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': window.PAPER_CONFIG.csrfToken }
        });
        
        if (response.ok) {
            showToast('Extracción eliminada', 'success');
            setTimeout(() => location.reload(), 500);
        } else {
            showToast('Error al eliminar', 'error');
        }
    } catch (error) {
        console.error('Error deleting quote:', error);
        showToast('Error de conexión', 'error');
    }
};

/**
 * Muestra un mensaje toast temporal
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo: 'success', 'error', 'info'
 */
function showToast(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-error',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    const iconPath = {
        'success': 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
        'error': 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
        'info': 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
    }[type];
    
    const toast = document.createElement('div');
    toast.className = `alert ${alertClass} fixed top-4 right-4 w-auto shadow-lg z-50 transition-opacity duration-300`;
    toast.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${iconPath}" />
        </svg>
        <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-eliminar después de 3 segundos
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Exponer showToast globalmente para uso externo
window.showToast = showToast;

// ============================================
// Inicialización
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    if (!window.PAPER_CONFIG) {
        console.error('❌ PAPER_CONFIG not found!');
        showToast('Error de configuración', 'error');
        return;
    }
    
    const workspace = new PaperWorkspace(window.PAPER_CONFIG);
    workspace.init();
});