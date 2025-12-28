// ui/extraction/static/scripts/components/quote_manager.js

/**
 * QuoteManager Component
 * Maneja la creación y visualización de quotes
 */

class QuoteManager {
    constructor(options) {
        this.apiUrl = options.apiUrl;
        this.csrfToken = options.csrfToken;
        this.paperId = options.paperId;
        this.pdfViewer = options.pdfViewer;
        this.tagManager = options.tagManager;
        
        this.modal = document.getElementById('quote_modal');
        this.form = document.getElementById('quote-form');
        this.textDisplay = document.getElementById('modal_text_display');
        this.pageIndicator = document.getElementById('page-indicator-modal');
        this.quotesList = document.getElementById('quotes-list-container');
        
        if (!this.modal || !this.form) {
            throw new Error('Quote modal or form not found');
        }
    }
    
    init() {
        console.log('💬 Initializing Quote Manager...');
        
        // Escuchar selecciones de texto
        document.addEventListener('textSelected', (e) => {
            this.handleTextSelection(e.detail);
        });
        
        // Escuchar clicks en quotes existentes
        if (this.quotesList) {
            this.quotesList.addEventListener('click', (e) => {
                const quoteCard = e.target.closest('.quote-card');
                if (quoteCard) {
                    this.handleQuoteClick(quoteCard);
                }
            });
        }
        
        // Manejar submit del formulario
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });
        
        // Exponer función globalmente
        window.scrollToText = (text, page) => this.scrollToText(text, page);
        
        console.log('✅ Quote Manager ready');
    }
    
    handleTextSelection(selection) {
        console.log(`✂️ Text selected: page ${selection.page}`);
        
        // Actualizar UI del modal
        if (this.textDisplay) {
            this.textDisplay.value = selection.text;
        }
        
        if (this.pageIndicator) {
            this.pageIndicator.textContent = `Detectado en página: ${selection.page}`;
        }
        
        // Resetear tags
        this.tagManager.resetSelection();
        
        // Abrir modal
        this.modal.showModal();
    }
    
    handleQuoteClick(quoteCard) {
        const page = parseInt(quoteCard.dataset.page);
        const text = quoteCard.dataset.text;
        
        this.scrollToText(text, page);
    }
    
    scrollToText(text, page) {
        console.log(`📍 Scrolling to text on page ${page}`);
        
        // Scroll a la página
        this.pdfViewer.scrollToPage(page);
        
        // Intentar resaltar el texto
        setTimeout(() => {
            const found = window.find(text, false, false, true, false, true, false);
            if (!found) {
                console.warn('⚠️ Text not found in viewport');
            }
        }, 600);
    }
    
    async handleSubmit() {
        console.log('📤 Submitting quote...');
        
        const selectedTags = this.tagManager.getSelectedTags();
        
        if (selectedTags.length === 0) {
            alert("Selecciona al menos una etiqueta.");
            return;
        }
        
        const selection = this.pdfViewer.getCurrentSelection();
        
        const payload = {
            text_fragment: selection.text,
            paper_extraction_id: this.paperId,
            tags: selectedTags,
            location: {
                page: selection.page || 1
            }
        };
        
        console.log('🚀 Payload:', payload);
        
        try {
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(payload)
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('✅ Quote saved:', data);
                
                // Cerrar modal
                this.modal.close();
                
                // Recargar para actualizar la lista
                window.location.reload();
            } else {
                const error = await response.json();
                console.error('❌ Backend error:', error);
                alert(`Error: ${error.error || JSON.stringify(error)}`);
            }
        } catch (error) {
            console.error('❌ Network error:', error);
            alert(`Error de red: ${error.message}`);
        }
    }
}

window.QuoteManager = QuoteManager;