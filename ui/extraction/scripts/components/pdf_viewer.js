/**
 * PDFViewer Component
 * Responsibility: PDF Rendering, Highlighting, Lazy Loading
 * Style: Refactored for MacOS/Atlas.ti aesthetic
 */

class PDFViewer {
    constructor(config) {
        this.config = config;
        this.pdf = null;
        this.container = document.getElementById('pdf-viewer-container');
        this.loader = document.getElementById('pdf-loader');
        this.baseScale = 1.3;
        this.currentScale = this.baseScale;
        this.minScale = 0.8;
        this.maxScale = 2.5;
        this.scaleStep = 0.1;
        this.pagePlaceholders = {};
        
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
                    reject(new Error('PDF.js failed to load'));
                }
            }, 100);
        });
    }

    async loadPDF() {
        // Ensure this matches your CDN or local path
        pdfjsLib.GlobalWorkerOptions.workerSrc = 
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        const loadingTask = pdfjsLib.getDocument({
            url: this.config.pdfUrl,
            verbosity: 0
        });

        loadingTask.onProgress = (progress) => {
            if (progress.total > 0) {
                const percent = Math.round((progress.loaded / progress.total) * 100);
                this.updateLoader(`Loading PDF... ${percent}%`);
            }
        };

        this.pdf = await loadingTask.promise;
        console.log(`✅ PDF loaded: ${this.pdf.numPages} pages`);

        if (this.loader) this.loader.style.display = 'none';

        await this.renderPages();
        this.setupZoomControls();
    }

    async renderPages() {
        const firstPage = await this.pdf.getPage(1);
        const viewport = firstPage.getViewport({ scale: this.currentScale });
        const pageWidth = viewport.width;
        const pageHeight = viewport.height;

        // 1. Calculate Priority Pages
        const priorityPages = this.calculatePriorityPages();
        
        // 2. Create Placeholders
        const pagePlaceholders = this.createPlaceholders(pageWidth, pageHeight);
        
        // 3. Separate into Queues
        const { highPriorityQueue, lowPriorityQueue } = this.createRenderQueues(priorityPages);
        
        // 4. Render High Priority First
        for (const pageNum of highPriorityQueue) {
            await this.renderPage(pageNum, pagePlaceholders[pageNum]);
        }

        // 5. Render Low Priority with Yielding
        for (const pageNum of lowPriorityQueue) {
            await this.renderPage(pageNum, pagePlaceholders[pageNum]);
            if (pageNum % 5 === 0) await new Promise(r => setTimeout(r, 0)); // Yield to main thread
        }
    }

    calculatePriorityPages() {
        const priorityPages = new Set();
        
        // First 10 pages usually contain abstract/intro
        const initialPages = Math.min(10, this.pdf.numPages);
        for (let i = 1; i <= initialPages; i++) {
            priorityPages.add(i);
        }

        // Pages around existing quotes (+/- 5 context)
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
            // Mac Style: White paper, soft shadow, centered
            placeholder.className = 'pdf-page-placeholder relative mb-5 bg-white shadow-lg mx-auto';
            placeholder.style.width = `${pageWidth}px`;
            placeholder.style.height = `${pageHeight}px`;

            // Skeleton Loader (Mac Style)
            placeholder.innerHTML = `
                <div class="w-full h-full p-12 flex flex-col gap-6 animate-pulse">
                    <div class="h-8 w-3/4 bg-gray-100 rounded-md"></div>
                    <div class="h-4 w-full bg-gray-50 rounded-md"></div>
                    <div class="h-4 w-full bg-gray-50 rounded-md"></div>
                    <div class="h-4 w-5/6 bg-gray-50 rounded-md"></div>
                    <div class="mt-12 h-40 w-full bg-gray-100 rounded-xl"></div>
                    <div class="mt-6 h-4 w-full bg-gray-50 rounded-md"></div>
                </div>
            `;

            this.container.appendChild(placeholder);
            placeholders[i] = placeholder;
            this.pagePlaceholders[i] = placeholder;
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
            const viewport = page.getViewport({ scale: this.currentScale });

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
                --scale-factor: ${this.currentScale};
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

        // Apply Highlight Style
        for (let i = startSpanIdx; i <= endSpanIdx; i++) {
            const span = textSpans[i];
            if (!span.classList.contains('highlight-quote')) {
                span.classList.add('highlight-quote');
                span.dataset.quoteId = quote.id;
                
                // Mac/Atlas.ti Style Highlight:
                // Yellow tint, multiply blend mode for realism
                span.style.backgroundColor = 'rgba(255, 240, 0, 0.4)';
                span.style.mixBlendMode = 'multiply';
                span.style.cursor = 'pointer';
                span.title = `Quote #${quote.id}`;
                
                // Add Hover Effect class via JS or ensure CSS handles it
                span.addEventListener('mouseenter', () => {
                    span.style.backgroundColor = 'rgba(255, 240, 0, 0.6)';
                });
                span.addEventListener('mouseleave', () => {
                    span.style.backgroundColor = 'rgba(255, 240, 0, 0.4)';
                });
                
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
            console.warn(`⚠️ Page ${pageNum} not rendered yet`);
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
            // Clear inline styles
            span.style.backgroundColor = '';
            span.style.cursor = '';
            span.style.mixBlendMode = '';
            span.title = '';
            delete span.dataset.quoteId;

            // Clone/replace to strip event listeners
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
            .replace(/\u00A0/g, '') // Remove non-breaking spaces
            .toLowerCase();
    }

    updateLoader(message) {
        if (this.loader) {
            // Assuming the loader structure matches the new Mac spinner
            const text = this.loader.querySelector('.loading-text');
            if (text) text.textContent = message;
        }
    }

    showError(message) {
        if (this.loader) {
            this.loader.innerHTML = `
                <div class="text-center p-8 bg-white/90 backdrop-blur-sm rounded-xl border border-red-100 shadow-xl">
                    <div class="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                        </svg>
                    </div>
                    <h3 class="font-bold text-lg mb-1 text-gray-900">PDF Load Error</h3>
                    <p class="text-sm text-gray-500 mb-6 max-w-xs mx-auto">${message}</p>
                    <button onclick="location.reload()" class="btn btn-sm btn-error bg-red-600 hover:bg-red-700 text-white border-none shadow-md">
                        Retry
                    </button>
                </div>
            `;
        }
    }

    // Zoom Methods
    setupZoomControls() {
        const zoomInBtn = document.getElementById('zoom-in-btn');
        const zoomOutBtn = document.getElementById('zoom-out-btn');
        const zoomResetBtn = document.getElementById('zoom-reset-btn');

        console.log('Setting up zoom controls:', { zoomInBtn, zoomOutBtn, zoomResetBtn });

        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => {
                console.log('Zoom in clicked');
                this.zoomIn();
            });
        }
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => {
                console.log('Zoom out clicked');
                this.zoomOut();
            });
        }
        if (zoomResetBtn) {
            zoomResetBtn.addEventListener('click', () => {
                console.log('Zoom reset clicked');
                this.resetZoom();
            });
        }
    }

    zoomIn() {
        console.log('zoomIn called, currentScale:', this.currentScale);
        this.currentScale = Math.min(this.currentScale + this.scaleStep, this.maxScale);
        console.log('New scale:', this.currentScale);
        this.applyZoom();
    }

    zoomOut() {
        console.log('zoomOut called, currentScale:', this.currentScale);
        this.currentScale = Math.max(this.currentScale - this.scaleStep, this.minScale);
        console.log('New scale:', this.currentScale);
        this.applyZoom();
    }

    resetZoom() {
        console.log('resetZoom called');
        this.currentScale = this.baseScale;
        console.log('Reset to:', this.currentScale);
        this.applyZoom();
    }

    applyZoom() {
        // Update zoom level display
        const zoomLevelElement = document.getElementById('zoom-level');
        if (zoomLevelElement) {
            zoomLevelElement.textContent = Math.round(this.currentScale * 100) + '%';
        }

        // Calculate zoom ratio based on current vs base scale
        // This allows us to use CSS transform without re-rendering
        const zoomRatio = this.currentScale / this.baseScale;
        
        console.log(`Applying zoom with transform scale: ${zoomRatio}`);

        // Apply CSS transform to the entire PDF container
        // This is instant and doesn't require re-rendering
        if (this.container) {
            this.container.style.transform = `scale(${zoomRatio})`;
            this.container.style.transformOrigin = 'top center';
            this.container.style.transition = 'transform 0.2s ease-out';
        }
    }
}

window.PDFViewer = PDFViewer;