/**
 * QuoteManager Component
 * Responsibility: Quote CRUD, Modal Management, Sidebar UI Updates
 * Style: Refactored for MacOS/Atlas.ti aesthetic
 */

class QuoteManager {
    constructor(config) {
        this.config = config;
        this.currentSelection = null;
        this.modal = document.getElementById('quote_modal');
        this.form = document.getElementById('quote-form');
        this.quotesList = document.getElementById('quotes-list-container');
        
        // UI Elements inside modal
        this.tagsCounter = document.getElementById('tags-counter');
        this.searchInput = document.getElementById('tag-search-input');
        
        console.log('💬 QuoteManager initialized');
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Form Submit
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createQuote();
            });
        }

        // Listen for Text Selection (Triggered by PaperWorkspace)
        window.addEventListener('text:selected', (e) => {
            this.showQuoteModal(e.detail.text, e.detail.page);
        });

        // Listen for sidebar quote clicks (scrolling)
        window.addEventListener('quote:click', (e) => {
            this.scrollToQuoteInSidebar(e.detail.quoteId);
        });

        // Listen for checkbox changes in modal to update counter
        if (this.modal) {
            this.modal.addEventListener('change', (e) => {
                if (e.target.classList.contains('tag-checkbox')) {
                    this.updateModalCounter();
                }
            });
        }
    }

    showQuoteModal(text, page) {
        // Validar que el paper no esté completado
        if (window.PAPER_CONFIG && window.PAPER_CONFIG.paperStatus === 'COMPLETED') {
            if (window.showToast) {
                window.showToast('Cannot add extractions to a completed paper', 'error');
            }
            return;
        }

        this.currentSelection = { text, page };

        const textArea = document.getElementById('selected-text');
        const pageInfo = document.getElementById('page-info');

        if (!textArea || !this.modal) {
            console.error('❌ Modal elements not found');
            return;
        }

        textArea.value = text;
        if (pageInfo) {
            pageInfo.textContent = `Page ${page}`;
        }

        // Reset Form
        this.form.querySelectorAll('input[name="tags"]').forEach(cb => {
            cb.checked = false;
        });

        // Reset Search & Counter
        if (this.searchInput) {
            this.searchInput.value = '';
            // Trigger input event to reset filter visibility
            this.searchInput.dispatchEvent(new Event('input')); 
        }
        this.updateModalCounter();

        // Show Modal
        this.modal.showModal();
    }

    updateModalCounter() {
        if (!this.tagsCounter) return;
        const count = this.form.querySelectorAll('input[name="tags"]:checked').length;
        
        this.tagsCounter.textContent = count === 0 ? '0 selected' : 
                                       count === 1 ? '1 selected' : 
                                       `${count} selected`;
        
        if (count > 0) {
            this.tagsCounter.classList.add('text-blue-600', 'font-bold');
            this.tagsCounter.classList.remove('text-gray-400');
        } else {
            this.tagsCounter.classList.remove('text-blue-600', 'font-bold');
            this.tagsCounter.classList.add('text-gray-400');
        }
    }

    async createQuote() {
        const formData = new FormData(this.form);
        const tags = formData.getAll('tags').map(id => parseInt(id));

        if (tags.length === 0) {
            // Use global toast instead of alert
            if (window.showToast) window.showToast('Please select at least one tag', 'error');
            else alert('Please select at least one tag');
            return;
        }

        // Show loading state on button
        const submitBtn = this.form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading loading-spinner loading-xs"></span> Saving...';

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
                
                // Dispatch event for PDFViewer to highlight
                window.dispatchEvent(new CustomEvent('quote:created', { 
                    detail: { quote: responseData.quote } 
                }));
                
                // Use global Mac-style toast
                if (window.showToast) window.showToast('Extraction saved successfully', 'success');
                
                window.getSelection().removeAllRanges();

            } else {
                if (window.showToast) window.showToast(`Error: ${responseData.error}`, 'error');
            }
        } catch (error) {
            console.error('❌ Network error:', error);
            if (window.showToast) window.showToast('Network error', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    }

    /**
     * Generates the new Card UI dynamically matching quote_list.html
     */
    addQuoteToSidebar(quote) {
        if (!this.quotesList) return;

        const emptyState = this.quotesList.querySelector('#empty-quotes-state');
        if (emptyState) emptyState.remove();

        const quoteCard = document.createElement('div');
        // Matches new CSS classes: Group, Relative, rounded-xl, borders
        quoteCard.className = 'group relative bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-blue-300 transition-all duration-200 ease-out quote-card cursor-pointer mb-3';
        quoteCard.dataset.quoteId = quote.id;
        quoteCard.dataset.page = quote.location.page || 1;
        
        // Add click listener for scrolling
        quoteCard.onclick = () => window.scrollToQuote(quote.id, quote.location.page || 1);

        // Generate Tags HTML (Pills with opacity)
        const tagsHtml = quote.tags.map(tag => `
            <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold border border-transparent" 
                  style="background-color: ${tag.color}15; color: ${tag.color};">
                ${tag.name}
            </span>
        `).join('');

        quoteCard.innerHTML = `
            <div class="p-4">
                <div class="flex justify-between items-start mb-2">
                    <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-gray-100 text-gray-500 border border-gray-200">
                        Pg. ${quote.location.page || '-'}
                    </span>
                    
                    <button type="button" 
                            class="btn btn-xs btn-square btn-ghost text-gray-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all duration-200"
                            onclick="event.stopPropagation(); deleteQuote(${quote.id})"
                            title="Delete Quote">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
                
                <blockquote class="relative border-l-2 border-green-500/50 pl-3 py-0.5 mb-3">
                    <p class="text-sm text-gray-800 leading-relaxed font-serif italic line-clamp-4">
                        "${quote.text_fragment}"
                    </p>
                </blockquote>
                
                <div class="flex flex-wrap gap-1.5">
                    ${tagsHtml}
                </div>
            </div>
        `;

        this.quotesList.insertBefore(quoteCard, this.quotesList.firstChild);

        // Animation Entrance
        quoteCard.style.opacity = '0';
        quoteCard.style.transform = 'translateY(-10px)';
        
        requestAnimationFrame(() => {
            quoteCard.style.opacity = '1';
            quoteCard.style.transform = 'translateY(0)';
        });
    }

    scrollToQuoteInSidebar(quoteId) {
        const quoteCard = document.querySelector(`[data-quote-id="${quoteId}"]`);
        if (quoteCard) {
            quoteCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            
            // Visual Highlight (Blue Ring)
            quoteCard.classList.add('ring-2', 'ring-blue-500', 'ring-offset-2');
            setTimeout(() => {
                quoteCard.classList.remove('ring-2', 'ring-blue-500', 'ring-offset-2');
            }, 2000);
        }
    }
}

window.QuoteManager = QuoteManager;