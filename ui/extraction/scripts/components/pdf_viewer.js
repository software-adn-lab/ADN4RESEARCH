/**
 * PDFViewer Component
 * Responsabilidad: Renderizar PDF, aplicar highlights, lazy loading
 */

class PDFViewer {
    constructor(config) {
        this.config = config;
        this.pdf = null;
        this.container = document.getElementById('pdf-viewer-container');
        this.loader = document.getElementById('pdf-loader');
        this.SCALE = 1.3;
        
        console.log('📄 PDFViewer initialized');
    }

    async init() {
        console.log('⏳ Loading PDF from:', this.config.pdfUrl);
        
        try {
            await this.waitForPDFJS();
            await this.loadPDF();
            console.log('✅ PDF loaded successfully');
        } catch (error) {
            console.error('❌ PDF load failed:', error);
            this.showError(error.message);
        }
    }

    async waitForPDFJS() {
        return new Promise((resolve, reject) => {
            if (typeof pdfjsLib !== 'undefined') {
                resolve();
                return;
            }

            let attempts = 0;
            const maxAttempts = 100;

            const checkInterval = setInterval(() => {
                attempts++;
                if (typeof pdfjsLib !== 'undefined') {
                    clearInterval(checkInterval);
                    resolve();
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    reject(new Error('PDF.js no se cargó'));
                }
            }, 100);
        });
    }

    async loadPDF() {
        pdfjsLib.GlobalWorkerOptions.workerSrc = 
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        const loadingTask = pdfjsLib.getDocument({
            url: this.config.pdfUrl,
            verbosity: 0
        });

        loadingTask.onProgress = (progress) => {
            if (progress.total > 0) {
                const percent = Math.round((progress.loaded / progress.total) * 100);
                this.updateLoader(`Cargando PDF... ${percent}%`);
            }
        };

        this.pdf = await loadingTask.promise;
        console.log(`✅ PDF loaded: ${this.pdf.numPages} pages`);

        if (this.loader) this.loader.style.display = 'none';

        await this.renderPages();
    }

    async renderPages() {
        const firstPage = await this.pdf.getPage(1);
        const viewport = firstPage.getViewport({ scale: this.SCALE });
        const pageWidth = viewport.width;
        const pageHeight = viewport.height;

        // 1. Calcular páginas prioritarias
        const priorityPages = this.calculatePriorityPages();
        
        // 2. Crear placeholders
        const pagePlaceholders = this.createPlaceholders(pageWidth, pageHeight);
        
        // 3. Separar en colas
        const { highPriorityQueue, lowPriorityQueue } = this.createRenderQueues(priorityPages);
        
        // 4. Renderizar
        for (const pageNum of highPriorityQueue) {
            await this.renderPage(pageNum, pagePlaceholders[pageNum]);
        }

        for (const pageNum of lowPriorityQueue) {
            await this.renderPage(pageNum, pagePlaceholders[pageNum]);
            if (pageNum % 5 === 0) await new Promise(r => setTimeout(r, 0));
        }
    }

    calculatePriorityPages() {
        const priorityPages = new Set();
        
        // Primeras 10 páginas
        const initialPages = Math.min(10, this.pdf.numPages);
        for (let i = 1; i <= initialPages; i++) {
            priorityPages.add(i);
        }

        // Páginas con quotes ± 5
        if (this.config.existingQuotes && Array.isArray(this.config.existingQuotes)) {
            this.config.existingQuotes.forEach(quote => {
                const p = quote.location?.page || 0;
                for (let i = p - 5; i <= p + 5; i++) {
                    if (i >= 1 && i <= this.pdf.numPages) {
                        priorityPages.add(i);
                    }
                }
            });
        }

        return priorityPages;
    }

    createPlaceholders(pageWidth, pageHeight) {
        const placeholders = [];

        for (let i = 1; i <= this.pdf.numPages; i++) {
            const placeholder = document.createElement('div');
            placeholder.id = `page-placeholder-${i}`;
            placeholder.className = 'pdf-page-placeholder relative mb-5';
            placeholder.style.width = `${pageWidth}px`;
            placeholder.style.height = `${pageHeight}px`;
            placeholder.style.margin = '0 auto 20px';
            placeholder.style.backgroundColor = 'white';
            placeholder.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';

            placeholder.innerHTML = `
                <div class="w-full h-full p-8 flex flex-col gap-4 animate-pulse">
                    <div class="skeleton h-8 w-3/4 bg-gray-200"></div>
                    <div class="skeleton h-4 w-full bg-gray-200"></div>
                    <div class="skeleton h-4 w-full bg-gray-200"></div>
                    <div class="skeleton h-4 w-5/6 bg-gray-200"></div>
                    <div class="mt-8 skeleton h-32 w-full bg-gray-200"></div>
                    <div class="mt-4 skeleton h-4 w-full bg-gray-200"></div>
                </div>
            `;

            this.container.appendChild(placeholder);
            placeholders[i] = placeholder;
        }

        return placeholders;
    }

    createRenderQueues(priorityPages) {
        const highPriorityQueue = [];
        const lowPriorityQueue = [];

        for (let i = 1; i <= this.pdf.numPages; i++) {
            if (priorityPages.has(i)) {
                highPriorityQueue.push(i);
            } else {
                lowPriorityQueue.push(i);
            }
        }

        return { highPriorityQueue, lowPriorityQueue };
    }

    async renderPage(pageNum, container) {
        try {
            const page = await this.pdf.getPage(pageNum);
            const viewport = page.getViewport({ scale: this.SCALE });

            const pageDiv = document.createElement('div');
            pageDiv.className = 'page-container';
            pageDiv.dataset.pageNumber = pageNum;
            pageDiv.style.cssText = 'width: 100%; height: 100%; position: relative;';

            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const ctx = canvas.getContext('2d');

            const textLayer = document.createElement('div');
            textLayer.className = 'textLayer';
            textLayer.style.cssText = `
                position: absolute;
                left: 0; top: 0; right: 0; bottom: 0;
                overflow: hidden;
                opacity: 1;
                line-height: 1.0;
                --scale-factor: ${this.SCALE};
            `;

            pageDiv.appendChild(canvas);
            pageDiv.appendChild(textLayer);

            container.innerHTML = '';
            container.appendChild(pageDiv);

            await page.render({ canvasContext: ctx, viewport }).promise;

            const textContent = await page.getTextContent();
            await pdfjsLib.renderTextLayer({
                textContentSource: textContent,
                container: textLayer,
                viewport: viewport,
                textDivs: []
            }).promise;

            this.highlightQuotesOnPage(textLayer, pageNum);

        } catch (error) {
            console.error(`Error rendering page ${pageNum}:`, error);
        }
    }

    highlightQuotesOnPage(textLayer, pageNumber) {
        if (!this.config.existingQuotes || this.config.existingQuotes.length === 0) {
            return;
        }

        const quotesOnPage = this.config.existingQuotes.filter(quote => {
            return (quote.location?.page || 0) === pageNumber;
        });

        if (quotesOnPage.length === 0) return;

        console.log(`   🎨 Highlighting ${quotesOnPage.length} quotes on page ${pageNumber}`);

        quotesOnPage.forEach(quote => {
            this.highlightTextInLayer(textLayer, quote.text_fragment, quote);
        });
    }

    highlightTextInLayer(textLayer, searchText, quote) {
        const textSpans = Array.from(textLayer.querySelectorAll('span'));
        if (textSpans.length === 0) return;

        const searchStrict = this.normalizeStrict(searchText);
        if (!searchStrict) return;

        let fullTextStrict = '';
        const spanMap = [];

        textSpans.forEach((span, index) => {
            const spanTextStrict = this.normalizeStrict(span.textContent);
            spanMap.push({
                index: index,
                start: fullTextStrict.length,
                length: spanTextStrict.length,
                element: span
            });
            fullTextStrict += spanTextStrict;
        });

        let foundIndex = fullTextStrict.indexOf(searchStrict);

        if (foundIndex === -1 && searchStrict.length > 50) {
            const shortSearch = searchStrict.substring(0, 50);
            foundIndex = fullTextStrict.indexOf(shortSearch);
        }

        if (foundIndex === -1) {
            console.warn(`⚠️ Text not found for quote ${quote.id}`);
            return;
        }

        const endIndex = foundIndex + searchStrict.length;
        let startSpanIdx = -1;
        let endSpanIdx = -1;

        for (const map of spanMap) {
            const spanEnd = map.start + map.length;
            if (startSpanIdx === -1 && spanEnd > foundIndex) {
                startSpanIdx = map.index;
            }
            if (startSpanIdx !== -1 && map.start < endIndex) {
                endSpanIdx = map.index;
            }
        }

        if (startSpanIdx === -1 || endSpanIdx === -1) return;

        for (let i = startSpanIdx; i <= endSpanIdx; i++) {
            const span = textSpans[i];
            if (!span.classList.contains('highlight-quote')) {
                span.classList.add('highlight-quote');
                span.dataset.quoteId = quote.id;
                span.style.mixBlendMode = 'multiply';
                span.title = `Quote #${quote.id}`;
                
                span.addEventListener('click', (e) => {
                    e.stopPropagation();
                    window.dispatchEvent(new CustomEvent('quote:click', { 
                        detail: { quoteId: quote.id } 
                    }));
                });
            }
        }
    }

    highlightNewQuote(quote) {
        const pageNum = quote.location.page;
        const pageContainer = document.querySelector(`.page-container[data-page-number="${pageNum}"]`);
        
        if (!pageContainer) {
            console.warn(`⚠️ Page ${pageNum} not rendered`);
            return;
        }

        const textLayer = pageContainer.querySelector('.textLayer');
        if (!textLayer) return;

        console.log(`🎨 Highlighting new quote ${quote.id}`);
        this.highlightTextInLayer(textLayer, quote.text_fragment, quote);
    }

    removeQuoteHighlight(quoteId) {
        const id = parseInt(quoteId);
        const highlightedSpans = document.querySelectorAll(`.highlight-quote[data-quote-id="${id}"]`);

        highlightedSpans.forEach(span => {
            span.classList.remove('highlight-quote');
            span.style.backgroundColor = '';
            span.style.cursor = '';
            span.style.mixBlendMode = '';
            span.title = '';
            delete span.dataset.quoteId;

            const newSpan = span.cloneNode(true);
            span.parentNode.replaceChild(newSpan, span);
        });

        if (this.config.existingQuotes) {
            this.config.existingQuotes = this.config.existingQuotes.filter(q => q.id !== id);
        }
    }

    normalizeStrict(text) {
        if (!text) return '';
        return text
            .replace(/\s+/g, '')
            .replace(/\u00A0/g, '')
            .toLowerCase();
    }

    getCurrentSelection() {
        return { text: '', page: 1 };
    }

    updateLoader(message) {
        if (this.loader) {
            const text = this.loader.querySelector('span:last-child');
            if (text) text.textContent = message;
        }
    }

    showError(message) {
        if (this.loader) {
            this.loader.innerHTML = `
                <div class="text-center p-8">
                    <svg class="w-16 h-16 mx-auto mb-4 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <h3 class="font-bold text-lg mb-2 text-error">Error cargando PDF</h3>
                    <p class="text-sm mb-4">${message}</p>
                    <button onclick="location.reload()" class="btn btn-primary btn-sm">Reintentar</button>
                </div>
            `;
        }
    }
}

window.PDFViewer = PDFViewer;