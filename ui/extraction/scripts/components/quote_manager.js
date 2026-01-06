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
        this.deleteApiUrl = options.deleteApiUrl;

        this.currentSelection = { text: '', page: 1 };

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

        // 1. Verificar que el contenedor existe
        if (!this.quotesList) {
            console.error('❌ Error CRÍTICO: No se encontró el elemento con id "quotes-list-container"');
            return;
        }

        console.log('✅ Container found, adding listener to:', this.quotesList);

        // 2. Listener con Logs de Depuración
        this.quotesList.addEventListener('click', (e) => {
            // Log para ver qué estás clickeando exactamente
            console.log('⚡ Click detectado en:', e.target);

            // Buscar el botón (incluso si clickeaste el SVG o el Path interno)
            const deleteBtn = e.target.closest('.delete-quote-btn');

            console.log('   ¿Es botón de borrar?:', deleteBtn ? 'SÍ' : 'NO');

            if (deleteBtn) {
                // DETENER TODO: Evita que el click pase a la tarjeta y haga scroll
                e.stopPropagation();
                e.preventDefault();

                const quoteId = deleteBtn.dataset.quoteId;
                console.log('   Intentando borrar ID:', quoteId);

                if (quoteId) {
                    this.handleDeleteQuote(quoteId);
                } else {
                    console.error('❌ El botón no tiene atributo data-quote-id', deleteBtn);
                    alert('Error: Botón sin ID de quote');
                }
                return; // Importante: Salir aquí para no ejecutar el click de la tarjeta
            }

            // Si no fue el botón de borrar, verificamos si fue la tarjeta
            const quoteCard = e.target.closest('.quote-card');
            if (quoteCard) {
                console.log('   Click en tarjeta (scroll)');
                this.handleQuoteClick(quoteCard);
            }
        });

        // Submit del formulario
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSubmit();
            });
        }

        // Helper global
        window.scrollToText = (text, page) => this.scrollToText(text, page);

        console.log('✅ Listeners listos');
    }

    handleTextSelection(selection) {
        console.log(`✂️ Text selected: page ${selection.page}`);

        // ✅ Guardar selección en QuoteManager (fallback)
        this.currentSelection = selection;

        // Actualizar UI del modal
        if (this.textDisplay) {
            this.textDisplay.value = selection.text;
        }

        if (this.pageIndicator) {
            this.pageIndicator.textContent = `Detectado en página: ${selection.page}`;
        }

        // Resetear tags
        if (this.tagManager) {
            this.tagManager.resetSelection();
        }

        // Abrir modal
        if (this.modal) {
            this.modal.showModal();
        }
    }

    handleQuoteClick(quoteCard) {
        const page = parseInt(quoteCard.dataset.page);
        const text = quoteCard.dataset.text;

        this.scrollToText(text, page);
    }

    scrollToText(text, page) {
        console.log(`📍 Scrolling to text on page ${page}`);

        if (this.pdfViewer) {
            this.pdfViewer.scrollToPage(page);
        } else {
            const pageElement = document.getElementById(`page-${page}`);
            if (pageElement) {
                pageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

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

        // ✅ Intentar obtener selección de pdfViewer, sino usar fallback
        let selection;

        if (this.pdfViewer && typeof this.pdfViewer.getCurrentSelection === 'function') {
            selection = this.pdfViewer.getCurrentSelection();
            console.log('   Using selection from pdfViewer:', selection);
        } else {
            selection = this.currentSelection;
            console.log('   Using fallback selection:', selection);
        }

        // Validar que tenemos datos
        if (!selection || !selection.text) {
            console.error('❌ No selection data available');
            alert('Error: No se detectó texto seleccionado. Por favor, intenta de nuevo.');
            return;
        }

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
                // ✅ Agregar a existingQuotes del pdfViewer
                if (this.pdfViewer && this.pdfViewer.existingQuotes) {
                    this.pdfViewer.existingQuotes.push(data.quote);
                    console.log('   Added to pdfViewer.existingQuotes');

                    // ✅ Re-highlight la página donde se creó
                    const pageNumber = data.quote.location?.page;
                    if (pageNumber && this.pdfViewer.rehighlightPage) {
                        this.pdfViewer.rehighlightPage(pageNumber);
                    }
                }

                // ✅ OPCIÓN 1: Sin recargar (mejor UX)
                this.addQuoteToSidebar(data.quote);
                this.updateQuoteCount();
                this.showSuccessNotification('Quote guardada exitosamente');

                // ✅ OPCIÓN 2: Con recarga (comentar la línea anterior y descomentar esta)
                // window.location.reload();

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

    /**
     * Agregar quote al sidebar dinámicamente (sin recargar)
     */
    addQuoteToSidebar(quote) {
        const quotesList = document.getElementById('quotes-list-container');

        if (!quotesList) {
            console.warn('⚠️ Quotes list container not found, will reload instead');
            window.location.reload();
            return;
        }

        // Remover mensaje de "sin quotes" si existe
        const emptyState = quotesList.querySelector('#empty-quotes-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Crear elemento de quote
        const quoteCard = document.createElement('div');
        quoteCard.className = 'quote-card card bg-white border border-gray-200 shadow-sm hover:shadow-md hover:border-primary cursor-pointer transition-all group rounded-lg';
        quoteCard.dataset.quoteId = quote.id;
        quoteCard.dataset.page = quote.location.page || 1;
        quoteCard.dataset.text = quote.text_fragment;

        // Construir HTML de tags
        const tagsHtml = quote.tags.map(tag => `
            <span class="inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-medium ring-1 ring-inset ring-gray-500/10"
                  style="background-color: ${tag.color}20; color: ${tag.color}; border-color: ${tag.color}40;">
                ${tag.name}
            </span>
        `).join('');

        quoteCard.innerHTML = `
            <div class="card-body p-3">
                <div class="flex justify-between items-start mb-1">
                    <span class="badge badge-ghost badge-xs font-mono">Pg. ${quote.location.page || '?'}</span>
                    <span class="badge badge-success badge-xs gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        NUEVO
                    </span>
                </div>

                <p class="text-xs text-gray-600 line-clamp-3 italic group-hover:text-gray-900 border-l-2 border-gray-300 pl-2 group-hover:border-primary transition-colors">
                    "${quote.text_fragment}"
                </p>

                <div class="flex flex-wrap gap-1 mt-2">
                    ${tagsHtml}
                </div>
            </div>
        `;

        // Click handler
        quoteCard.addEventListener('click', () => {
            this.scrollToText(quote.text_fragment, quote.location.page);
        });

        // Agregar al inicio de la lista
        quotesList.insertBefore(quoteCard, quotesList.firstChild);

        // Animación de entrada
        quoteCard.style.opacity = '0';
        quoteCard.style.transform = 'translateY(-10px)';
        quoteCard.style.transition = 'all 0.3s ease-out';

        setTimeout(() => {
            quoteCard.style.opacity = '1';
            quoteCard.style.transform = 'translateY(0)';
        }, 10);

        console.log('✅ Quote added to sidebar');
    }
    async handleDeleteQuote(quoteId) {
        console.log(`🗑️ Delete quote requested: ${quoteId}`);

        if (!confirm('¿Estás seguro de que deseas eliminar esta extracción?')) {
            return;
        }

        try {
            const deleteUrl = `${this.deleteApiUrl}${quoteId}`;

            const response = await fetch(deleteUrl, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': this.csrfToken }
            });

            if (response.ok) {
                console.log('✅ Quote deleted successfully');

                // 1. Remover del Sidebar visualmente
                const quoteCard = document.querySelector(`.quote-card[data-quote-id="${quoteId}"]`);
                if (quoteCard) {
                    quoteCard.style.transform = 'translateX(20px)';
                    quoteCard.style.opacity = '0';
                    setTimeout(() => {
                        quoteCard.remove();
                        // Verificar si quedó vacío para mostrar el placeholder
                        if (!document.querySelector('.quote-card')) this.showEmptyState();
                    }, 300);
                }

                // 2. Actualizar contador (-1)
                this.updateQuoteCount(-1);

                // 3. Quitar highlight del PDF (sin recargar)
                if (this.pdfViewer && typeof this.pdfViewer.removeQuoteHighlight === 'function') {
                    this.pdfViewer.removeQuoteHighlight(quoteId);
                }

                this.showSuccessNotification('Quote eliminada');

            } else {
                const error = await response.json();
                alert(`Error al eliminar: ${error.error || 'Error desconocido'}`);
            }
        } catch (error) {
            console.error('❌ Network error:', error);
            alert(`Error de red: ${error.message}`);
        }
    }

    updateQuoteCount(delta = 1) {
        const counter = document.getElementById('quotes-count');
        if (counter) {
            let currentCount = parseInt(counter.textContent) || 0;
            const newCount = Math.max(0, currentCount + delta);
            counter.textContent = newCount;
        }
    }

    showEmptyState() {
        if (!this.quotesList) return;

        this.quotesList.innerHTML = `
            <div class="flex flex-col items-center justify-center h-40 text-gray-400" id="empty-quotes-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 mb-2 opacity-50">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <p class="text-sm font-medium">Sin extracciones</p>
                <p class="text-xs">Selecciona texto para comenzar</p>
            </div>
        `;
    }


    showSuccessNotification(message) {
        const toast = document.createElement('div');
        toast.className = 'alert alert-success fixed bottom-4 right-4 w-auto shadow-lg z-50 animate-fade-in';
        toast.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>${message}</span>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            toast.style.transition = 'all 0.3s ease-out';

            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

window.QuoteManager = QuoteManager;