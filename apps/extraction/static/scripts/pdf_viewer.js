class PDFViewer {
    constructor() {
        this.pdfDoc = null;
        this.currentPage = 1;
        this.totalPages = 0;
        this.scale = 1.5;
        this.canvas = document.getElementById('pdf-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.textLayer = document.getElementById('text-layer');
        this.highlightsLayer = document.getElementById('highlights-layer');

        this.quotes = [];
        this.availableTags = [];
        this.currentSelection = null;

        this.init();
    }

    async init() {
        if (!PDF_URL) {
            this.showError('No PDF file available for this study');
            return;
        }

        try {
            await this.loadPDF();
            await this.loadTags();
            await this.loadQuotes();
            this.setupEventListeners();
            this.renderPage(this.currentPage);
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to load PDF viewer');
        }
    }

    async loadPDF() {
        const loadingTask = pdfjsLib.getDocument(PDF_URL);
        this.pdfDoc = await loadingTask.promise;
        this.totalPages = this.pdfDoc.numPages;
        document.getElementById('page-count').textContent = this.totalPages;
    }

    async loadTags() {
        const response = await fetch(API_URLS.availableTags);
        const data = await response.json();
        this.availableTags = data.tags || [];
        this.renderTagsCheckboxes();
    }

    async loadQuotes() {
        const response = await fetch(API_URLS.listQuotes);
        const data = await response.json();
        this.quotes = data.quotes || [];
        this.updateQuoteCount();
        this.renderQuotesList();
        this.renderQuoteHighlights();
    }

    renderTagsCheckboxes() {
        const container = document.getElementById('tags-container');

        if (this.availableTags.length === 0) {
            container.innerHTML = '<p class="text-sm text-base-content/60 text-center py-4">No tags available</p>';
            return;
        }

        container.innerHTML = this.availableTags.map(tag => `
            <label class="flex items-center gap-2 p-2 hover:bg-base-300 rounded cursor-pointer">
                <input type="checkbox" 
                       class="checkbox checkbox-sm checkbox-primary tag-checkbox" 
                       value="${tag.id}" />
                <span class="badge badge-sm" style="background-color: ${tag.color || '#6366f1'}">
                    ${tag.name}
                </span>
                ${tag.is_mandatory ? '<span class="badge badge-xs badge-error">Required</span>' : ''}
            </label>
        `).join('');
    }

    async renderPage(pageNum) {
        if (pageNum < 1 || pageNum > this.totalPages) return;

        this.currentPage = pageNum;
        document.getElementById('page-num').value = pageNum;

        const page = await this.pdfDoc.getPage(pageNum);
        const viewport = page.getViewport({ scale: this.scale });

        this.canvas.height = viewport.height;
        this.canvas.width = viewport.width;

        // Render PDF page
        const renderContext = {
            canvasContext: this.ctx,
            viewport: viewport
        };
        await page.render(renderContext).promise;

        // Render text layer for selection
        const textContent = await page.getTextContent();
        this.renderTextLayer(textContent, viewport);

        // Render quote highlights
        this.renderQuoteHighlights();
    }

    renderTextLayer(textContent, viewport) {
        this.textLayer.innerHTML = '';
        this.textLayer.style.width = `${viewport.width}px`;
        this.textLayer.style.height = `${viewport.height}px`;

        pdfjsLib.renderTextLayer({
            textContent: textContent,
            container: this.textLayer,
            viewport: viewport,
            textDivs: []
        });
    }

    renderQuoteHighlights() {
        this.highlightsLayer.innerHTML = '';

        const pageQuotes = this.quotes.filter(q => q.page === this.currentPage);

        pageQuotes.forEach((quote, index) => {
            if (quote.location && quote.location.coordinates) {
                const { x1, y1, x2, y2 } = quote.location.coordinates;
                const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');

                rect.setAttribute('x', x1);
                rect.setAttribute('y', y1);
                rect.setAttribute('width', x2 - x1);
                rect.setAttribute('height', y2 - y1);
                rect.setAttribute('class', 'quote-highlight');
                rect.setAttribute('data-quote-id', quote.id);

                rect.addEventListener('click', () => this.highlightQuote(quote.id));

                this.highlightsLayer.appendChild(rect);
            }
        });
    }

    setupEventListeners() {
        // Navigation
        document.getElementById('prev-page').addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.renderPage(this.currentPage - 1);
            }
        });

        document.getElementById('next-page').addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.renderPage(this.currentPage + 1);
            }
        });

        document.getElementById('page-num').addEventListener('change', (e) => {
            const page = parseInt(e.target.value);
            this.renderPage(page);
        });

        // Zoom
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.scale = Math.min(this.scale + 0.25, 3);
            this.updateZoomLevel();
            this.renderPage(this.currentPage);
        });

        document.getElementById('zoom-out').addEventListener('click', () => {
            this.scale = Math.max(this.scale - 0.25, 0.5);
            this.updateZoomLevel();
            this.renderPage(this.currentPage);
        });

        // Text selection
        document.addEventListener('mouseup', () => this.handleTextSelection());

        // Quote form
        document.getElementById('quote-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createQuote();
        });

        document.getElementById('cancel-quote').addEventListener('click', () => {
            this.clearSelection();
        });

        // Tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Sidebar toggle
        document.getElementById('toggle-sidebar').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('collapsed');
        });
    }

    handleTextSelection() {
        const selection = window.getSelection();
        const text = selection.toString().trim();

        if (text.length === 0) return;

        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const canvasRect = this.canvas.getBoundingClientRect();

        // Calculate coordinates relative to canvas
        const x1 = (rect.left - canvasRect.left) * (this.canvas.width / canvasRect.width);
        const y1 = (rect.top - canvasRect.top) * (this.canvas.height / canvasRect.height);
        const x2 = (rect.right - canvasRect.left) * (this.canvas.width / canvasRect.width);
        const y2 = (rect.bottom - canvasRect.top) * (this.canvas.height / canvasRect.height);

        this.currentSelection = {
            text,
            page: this.currentPage,
            x1, y1, x2, y2
        };

        this.showQuoteForm();
    }

    showQuoteForm() {
        document.getElementById('selected-text').textContent = this.currentSelection.text;
        document.getElementById('selected-page').textContent = this.currentSelection.page;
        document.getElementById('coord-page').value = this.currentSelection.page;
        document.getElementById('coord-x1').value = this.currentSelection.x1;
        document.getElementById('coord-y1').value = this.currentSelection.y1;
        document.getElementById('coord-x2').value = this.currentSelection.x2;
        document.getElementById('coord-y2').value = this.currentSelection.y2;

        document.getElementById('quote-form').classList.remove('hidden');
        this.switchTab('create');
    }

    clearSelection() {
        this.currentSelection = null;
        document.getElementById('quote-form').classList.add('hidden');
        document.getElementById('quote-form').reset();

        // Clear checkboxes
        document.querySelectorAll('.tag-checkbox').forEach(cb => cb.checked = false);

        window.getSelection().removeAllRanges();
    }

    async createQuote() {
        const selectedTags = Array.from(document.querySelectorAll('.tag-checkbox:checked'))
            .map(cb => parseInt(cb.value));

        if (selectedTags.length === 0) {
            alert('Please select at least one tag');
            return;
        }

        const locationDescription = document.getElementById('location-description').value.trim();

        const quoteData = {
            extraction_id: EXTRACTION_ID,
            text: this.currentSelection.text,
            tag_ids: selectedTags,
            location: {
                page: this.currentSelection.page,
                text_location: locationDescription || `Page ${this.currentSelection.page}`,
                x1: this.currentSelection.x1,
                y1: this.currentSelection.y1,
                x2: this.currentSelection.x2,
                y2: this.currentSelection.y2
            }
        };

        try {
            const response = await fetch(API_URLS.createQuote, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify(quoteData)
            });

            if (!response.ok) {
                throw new Error('Failed to create quote');
            }

            const newQuote = await response.json();
            this.quotes.push(newQuote);

            this.updateQuoteCount();
            this.renderQuotesList();
            this.renderQuoteHighlights();
            this.clearSelection();

            this.showSuccess('Quote created successfully');
        } catch (error) {
            console.error('Error creating quote:', error);
            this.showError('Failed to create quote');
        }
    }

    renderQuotesList() {
        const container = document.getElementById('quotes-list');

        if (this.quotes.length === 0) {
            container.innerHTML = '<div class="text-center text-sm text-base-content/60 py-8">No quotes yet. Select text to create your first quote.</div>';
            return;
        }

        container.innerHTML = this.quotes.map(quote => `
            <div class="card bg-base-200 border border-base-300 hover:border-primary cursor-pointer transition-all"
                 data-quote-id="${quote.id}"
                 onclick="pdfViewer.goToQuote(${quote.id})">
                <div class="card-body p-3">
                    <div class="flex items-start justify-between mb-2">
                        <span class="badge badge-sm badge-primary">Page ${quote.page || '?'}</span>
                        <button class="btn btn-ghost btn-xs text-error" onclick="event.stopPropagation(); pdfViewer.deleteQuote(${quote.id})">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                        </button>
                    </div>
                    <p class="text-xs text-base-content leading-relaxed line-clamp-3">${quote.text}</p>
                    <div class="flex flex-wrap gap-1 mt-2">
                        ${quote.tags.map(tag => `
                            <span class="badge badge-xs" style="background-color: ${tag.color || '#6366f1'}">
                                ${tag.name}
                            </span>
                        `).join('')}
                    </div>
                </div>
            </div>
        `).join('');
    }

    goToQuote(quoteId) {
        const quote = this.quotes.find(q => q.id === quoteId);
        if (quote && quote.page) {
            this.renderPage(quote.page);
            this.highlightQuote(quoteId);
        }
    }

    highlightQuote(quoteId) {
        // Temporarily highlight the selected quote
        const highlight = this.highlightsLayer.querySelector(`[data-quote-id="${quoteId}"]`);
        if (highlight) {
            highlight.style.fill = 'rgba(239, 68, 68, 0.4)';
            highlight.style.strokeWidth = '4';

            setTimeout(() => {
                highlight.style.fill = 'rgba(124, 58, 237, 0.2)';
                highlight.style.strokeWidth = '2';
            }, 1000);
        }
    }

    async deleteQuote(quoteId) {
        if (!confirm('Are you sure you want to delete this quote?')) return;

        try {
            const response = await fetch(`/api/extraction/quotes/${quoteId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                }
            });

            if (!response.ok) throw new Error('Failed to delete quote');

            this.quotes = this.quotes.filter(q => q.id !== quoteId);
            this.updateQuoteCount();
            this.renderQuotesList();
            this.renderQuoteHighlights();

            this.showSuccess('Quote deleted successfully');
        } catch (error) {
            console.error('Error deleting quote:', error);
            this.showError('Failed to delete quote');
        }
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('tab-active'));
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('tab-active');

        document.getElementById('tab-create').classList.add('hidden');
        document.getElementById('tab-quotes').classList.add('hidden');
        document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    }

    updateQuoteCount() {
        const count = this.quotes.length;
        document.getElementById('quote-count').textContent = `${count} quote${count !== 1 ? 's' : ''}`;
        document.getElementById('quotes-tab-count').textContent = count;
    }

    updateZoomLevel() {
        document.getElementById('zoom-level').textContent = `${Math.round(this.scale * 100)}%`;
    }

    showSuccess(message) {
        // You can implement a toast notification here
        console.log('Success:', message);
    }

    showError(message) {
        alert(message);
    }
}

// Initialize viewer when DOM is ready
let pdfViewer;
document.addEventListener('DOMContentLoaded', () => {
    pdfViewer = new PDFViewer();
});