/**
 * Paper Workspace - Main Orchestrator
 * Coordinates PDFViewer, QuoteManager, and TagManager via event bus.
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
            // 1. Initialize Components
            // Assuming these classes are defined in their respective files
            this.pdfViewer = new PDFViewer(this.config);
            this.quoteManager = new QuoteManager(this.config);
            this.tagManager = new TagManager(this.config);

            // 2. Setup Global Event Listeners
            this.setupEventListeners();

            // 3. Boot Components
            this.quoteManager.init();
            this.tagManager.init();
            await this.pdfViewer.init();

            console.log('✅ Workspace ready');
        } catch (error) {
            console.error('❌ Init failed:', error);
            showToast('Failed to initialize workspace', 'error');
        }
    }

    setupEventListeners() {
        // ============================================
        // 1. PDF Text Selection Listener (CORREGIDO)
        // ============================================
        
        // Ahora escuchamos en el documento pero filtramos el origen
        document.addEventListener('mouseup', (e) => {
            const container = document.getElementById('pdf-viewer-container');
            
            // 1. Si no existe el contenedor o el click no fue dentro de él, ignorar
            if (!container || !container.contains(e.target)) return;

            const selection = window.getSelection();
            
            // 2. Verificar si la selección en sí misma inicia dentro del contenedor
            // (selection.anchorNode es el nodo donde empieza la selección)
            const anchorNode = selection.anchorNode;
            if (!anchorNode || !container.contains(anchorNode.nodeType === 3 ? anchorNode.parentNode : anchorNode)) {
                return;
            }

            const text = selection.toString().trim();
            
            // Ignorar selecciones accidentales muy cortas
            if (text.length < 5) return;

            let pageNumber = 1;
            let node = selection.anchorNode;
            
            // Navegar hacia arriba para encontrar el contenedor de la página
            if (node && node.nodeType === 3) node = node.parentNode;
            if (node) {
                const pageContainer = node.closest('.page-container');
                if (pageContainer) {
                    pageNumber = parseInt(pageContainer.dataset.pageNumber) || 1;
                }
            }

            // Disparar evento
            window.dispatchEvent(new CustomEvent('text:selected', {
                detail: { text, page: pageNumber }
            }));
        });

        // ============================================
        // 2. Update PDF Highlights when Quote Created
        // ============================================
        window.addEventListener('quote:created', (e) => {
            this.config.existingQuotes = this.config.existingQuotes || [];
            this.config.existingQuotes.push(e.detail.quote);
            
            // Trigger visual highlight in PDFViewer
            if (this.pdfViewer && typeof this.pdfViewer.highlightNewQuote === 'function') {
                this.pdfViewer.highlightNewQuote(e.detail.quote);
            }
        });

        // ============================================
        // 3. Complete Paper Action
        // ============================================
        const completeBtn = document.getElementById('complete-paper-btn');
        if (completeBtn) {
            // Remove old listeners to prevent duplicates if re-initialized
            const newBtn = completeBtn.cloneNode(true);
            completeBtn.parentNode.replaceChild(newBtn, completeBtn);
            newBtn.addEventListener('click', this.handleCompletePaper.bind(this));
            console.log('✅ Complete button listener attached');
        }
    }

    /**
     * Handles the paper completion process
     */
    async handleCompletePaper(e) {
        const btn = e.currentTarget;
        
        // Native confirmation (clean and simple)
        const confirmed = confirm(
            'Are you sure you want to finish the extraction for this paper?\n\n' +
            'Please verify that:\n' +
            '• You have extracted all relevant quotations.\n' +
            '• All mandatory tags are covered.\n\n' +
            'This action will mark the paper as COMPLETED.'
        );
        
        if (!confirmed) return;
        
        // UI Loading State
        const originalContent = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `
            <span class="loading loading-spinner loading-xs"></span>
            Finishing...
        `;
        
        try {
            const response = await fetch(this.config.paperCompleteUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: 'COMPLETED' })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                showToast('Paper completed successfully', 'success');
                
                // Visual Success State before reload
                btn.classList.remove('btn-primary', 'bg-blue-600');
                btn.classList.add('btn-success', 'text-white');
                btn.innerHTML = 'Done!';

                setTimeout(() => {
                    // Optional: Redirect to dashboard or reload
                    window.location.reload(); 
                }, 1000);
                
            } else {
                throw new Error(data.error || 'Unknown server error');
            }
            
        } catch (error) {
            console.error('Error completing paper:', error);
            showToast(error.message || 'Connection error', 'error');
            
            // Reset Button
            btn.disabled = false;
            btn.innerHTML = originalContent;
        }
    }
}

// ============================================
// Global Functions (Legacy Support / Inline Calls)
// ============================================

/**
 * Scrolls to a specific quote in the PDF Viewer
 * Used by the Quote List click event
 */
window.scrollToQuote = function(quoteId, page) {
    // Attempt to find the text layer for that page
    const pageEl = document.querySelector(`[data-page-number="${page}"]`);
    if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Optional: Flash effect on the specific highlight if possible
        // This depends on how PDFViewer identifies highlights
        const highlight = document.querySelector(`.highlight[data-quote-id="${quoteId}"]`);
        if (highlight) {
            highlight.classList.add('ring-2', 'ring-offset-2', 'ring-yellow-400', 'transition-all');
            setTimeout(() => highlight.classList.remove('ring-2', 'ring-offset-2', 'ring-yellow-400'), 2000);
        }
    } else {
        showToast(`Page ${page} is not currently rendered`, 'info');
    }
};

/**
 * Deletes a quote via API
 * Used by the Quote List delete button
 */
window.deleteQuote = async function(quoteId) {
    if (!confirm('Are you sure you want to delete this extraction?')) return;
    
    // Find the button to show loading state (optional, relying on toast for now)
    
    const url = window.PAPER_CONFIG.quoteDeleteUrlTemplate.replace('0', quoteId).replace('{id}', quoteId);
    
    try {
        const response = await fetch(url, {
            method: 'POST', // or DELETE depending on your Django view setup
            headers: { 
                'X-CSRFToken': window.PAPER_CONFIG.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Extraction deleted', 'success');
            
            // Animate removal from DOM if element exists
            const card = document.querySelector(`.quote-card[data-quote-id="${quoteId}"]`);
            if (card) {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '0';
                card.style.transform = 'translateX(-10px)';
                setTimeout(() => card.remove(), 300);
            }
            
            // Optionally dispatch event to update PDF highlights
            window.dispatchEvent(new CustomEvent('quote:deleted', { detail: { id: quoteId } }));
            
        } else {
            showToast('Could not delete extraction', 'error');
        }
    } catch (error) {
        console.error('Error deleting quote:', error);
        showToast('Connection error', 'error');
    }
};

/**
 * Displays a Mac-style Toast Notification
 * @param {string} message - Text to display
 * @param {string} type - 'success' | 'error' | 'info'
 */
window.showToast = function(message, type = 'info') {
    // 1. Remove existing toasts to prevent stacking overload
    const existing = document.querySelectorAll('.custom-toast');
    existing.forEach(el => el.remove());

    // 2. Define Styles based on Type
    let icon, bgClass, borderClass, textClass;

    if (type === 'success') {
        icon = `<svg class="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
        bgClass = 'bg-white/90';
        borderClass = 'border-green-100';
    } else if (type === 'error') {
        icon = `<svg class="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
        bgClass = 'bg-white/90';
        borderClass = 'border-red-100';
    } else {
        icon = `<svg class="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`;
        bgClass = 'bg-white/90';
        borderClass = 'border-gray-200';
    }

    // 3. Create Element (Mac Notification Style)
    const toast = document.createElement('div');
    toast.className = `custom-toast fixed top-5 right-5 z-[9999] flex items-center gap-3 px-4 py-3 
                       ${bgClass} backdrop-blur-md border ${borderClass} 
                       rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] 
                       transform transition-all duration-300 translate-x-10 opacity-0`;
    
    toast.innerHTML = `
        <div class="flex-shrink-0">${icon}</div>
        <div class="text-sm font-medium text-gray-800">${message}</div>
    `;

    document.body.appendChild(toast);

    // 4. Animate In
    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-10', 'opacity-0');
    });

    // 5. Auto Dismiss
    setTimeout(() => {
        toast.classList.add('opacity-0', '-translate-y-2');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
};

// ============================================
// Main Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    if (!window.PAPER_CONFIG) {
        console.error('❌ PAPER_CONFIG not found in DOM.');
        return;
    }
    
    const workspace = new PaperWorkspace(window.PAPER_CONFIG);
    workspace.init();
});