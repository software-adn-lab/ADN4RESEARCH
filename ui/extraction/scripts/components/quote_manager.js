/**
 * QuoteManager Component
 * Responsabilidad: CRUD de quotes, gestión del modal, actualización del sidebar
 */

class QuoteManager {
    constructor(config) {
        this.config = config;
        this.currentSelection = null;
        this.modal = document.getElementById('quote_modal');
        this.form = document.getElementById('quote-form');
        this.quotesList = document.getElementById('quotes-list-container');
        
        console.log('💬 QuoteManager initialized');
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Submit formulario
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createQuote();
            });
        }

        // Escuchar evento de selección de texto
        window.addEventListener('text:selected', (e) => {
            this.showQuoteModal(e.detail.text, e.detail.page);
        });

        // Escuchar clicks en quotes del sidebar
        window.addEventListener('quote:click', (e) => {
            this.scrollToQuoteInSidebar(e.detail.quoteId);
        });
    }

    showQuoteModal(text, page) {
        this.currentSelection = { text, page };

        const textArea = document.getElementById('selected-text');
        const pageInfo = document.getElementById('page-info');

        if (!textArea || !this.modal) {
            console.error('❌ Modal elements not found');
            return;
        }

        textArea.value = text;
        if (pageInfo) {
            pageInfo.textContent = `Página ${page}`;
        }

        // Reset tags
        this.form.querySelectorAll('input[name="tags"]').forEach(cb => {
            cb.checked = false;
        });

        this.modal.showModal();
    }

    async createQuote() {
        const formData = new FormData(this.form);
        const tags = formData.getAll('tags').map(id => parseInt(id));

        if (tags.length === 0) {
            alert('Selecciona al menos una etiqueta');
            return;
        }

        const payload = {
            text_fragment: this.currentSelection.text,
            paper_extraction_id: this.config.paperId,
            tags: tags,
            location: { page: this.currentSelection.page }
        };

        try {
            const response = await fetch(this.config.quoteCreateUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.config.csrfToken
                },
                body: JSON.stringify(payload)
            });

            const responseData = await response.json();

            if (response.ok) {
                console.log('✅ Quote created:', responseData.quote);
                
                this.modal.close();
                this.addQuoteToSidebar(responseData.quote);
                
                // Disparar eventos para otros componentes
                window.dispatchEvent(new CustomEvent('quote:created', { 
                    detail: { quote: responseData.quote } 
                }));
                
                this.showSuccessNotification('Quote creada exitosamente');
                window.getSelection().removeAllRanges();

            } else {
                alert(`Error: ${responseData.error}`);
            }
        } catch (error) {
            console.error('❌ Network error:', error);
            alert('Error de red');
        }
    }

    addQuoteToSidebar(quote) {
        if (!this.quotesList) return;

        const emptyState = this.quotesList.querySelector('#empty-quotes-state');
        if (emptyState) emptyState.remove();

        const quoteCard = document.createElement('div');
        quoteCard.className = 'card bg-white border hover:shadow-md transition group quote-card';
        quoteCard.dataset.quoteId = quote.id;
        quoteCard.dataset.page = quote.location.page || 1;

        const tagsHtml = quote.tags.map(tag => `
            <span class="badge badge-xs" style="background-color: ${tag.color}20; color: ${tag.color}">
                ${tag.name}
            </span>
        `).join('');

        quoteCard.innerHTML = `
            <div class="card-body p-3">
                <div class="flex justify-between items-start mb-2">
                    <span class="badge badge-ghost badge-xs">Pg. ${quote.location.page || '?'}</span>
                    <span class="badge badge-success badge-xs gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        NUEVO
                    </span>
                </div>
                <p class="text-xs text-gray-600 line-clamp-3 italic cursor-pointer hover:text-gray-900 border-l-2 border-gray-300 pl-2 hover:border-primary transition-colors"
                   onclick="scrollToQuote(${quote.id}, ${quote.location.page || 1})">
                    "${quote.text_fragment}"
                </p>
                <div class="flex flex-wrap gap-1 mt-2">${tagsHtml}</div>
            </div>
        `;

        this.quotesList.insertBefore(quoteCard, this.quotesList.firstChild);

        // Animación
        quoteCard.style.opacity = '0';
        quoteCard.style.transform = 'translateY(-10px)';
        quoteCard.style.transition = 'all 0.3s ease-out';
        setTimeout(() => {
            quoteCard.style.opacity = '1';
            quoteCard.style.transform = 'translateY(0)';
        }, 10);
    }

    scrollToQuoteInSidebar(quoteId) {
        const quoteCard = document.querySelector(`[data-quote-id="${quoteId}"]`);
        if (quoteCard) {
            quoteCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            quoteCard.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
            setTimeout(() => {
                quoteCard.classList.remove('ring-2', 'ring-primary', 'ring-offset-2');
            }, 2000);
        }
    }

    showSuccessNotification(message) {
        const toast = document.createElement('div');
        toast.className = 'alert alert-success fixed bottom-4 right-4 w-auto shadow-lg z-50';
        toast.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>${message}</span>
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'all 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

window.QuoteManager = QuoteManager;