// ui/extraction/static/scripts/components/pdf_viewer.js

/**
 * PDFViewer Component
 * Maneja el renderizado del PDF y la selección de texto
 */

class PDFViewer {
    constructor(options) {
        this.container = document.querySelector(options.containerSelector);
        this.loader = document.querySelector(options.loaderSelector);
        this.pdfUrl = options.pdfUrl;
        this.existingQuotes = options.existingQuotes || [];

        this.pdf = null;
        this.currentSelection = { text: '', page: 1 };

        if (!this.container) {
            throw new Error('PDF container not found');
        }

        // Verificar PDF.js
        if (typeof pdfjsLib === 'undefined') {
            throw new Error('PDF.js library not loaded');
        }

        pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }

    async init() {
        console.log('📄 Initializing PDF Viewer...');

        try {
            // Cargar PDF
            const loadingTask = pdfjsLib.getDocument(this.pdfUrl);

            loadingTask.onProgress = (progress) => {
                if (progress.total > 0) {
                    const percent = Math.round((progress.loaded / progress.total) * 100);
                    this.updateLoader(`Cargando Documento... ${percent}%`);
                }
            };

            this.pdf = await loadingTask.promise;
            console.log(`✅ PDF loaded: ${this.pdf.numPages} pages`);

            // Ocultar loader
            if (this.loader) {
                this.loader.style.display = 'none';
            }

            // Renderizar páginas
            for (let pageNum = 1; pageNum <= this.pdf.numPages; pageNum++) {
                await this.renderPage(pageNum);
            }

            // Configurar event listeners
            this.setupEventListeners();

            console.log('✅ PDF Viewer ready');

        } catch (error) {
            console.error('❌ Error loading PDF:', error);
            this.showError(error.message);
        }
    }

    async renderPage(pageNumber) {
        const page = await this.pdf.getPage(pageNumber);
        const scale = 1.3;
        const viewport = page.getViewport({ scale });

        // Crear contenedor
        const pageDiv = document.createElement('div');
        pageDiv.className = 'page-container';
        pageDiv.id = `page-${pageNumber}`;
        pageDiv.dataset.pageNumber = pageNumber;
        pageDiv.style.width = `${viewport.width}px`;
        pageDiv.style.height = `${viewport.height}px`;

        // Canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        // Text layer
        const textLayer = document.createElement('div');
        textLayer.className = 'textLayer';
        textLayer.style.cssText = `position: absolute; top: 0; left: 0; width: ${viewport.width}px; height: ${viewport.height}px; --scale-factor: ${scale};`;

        pageDiv.appendChild(canvas);
        pageDiv.appendChild(textLayer);
        this.container.appendChild(pageDiv);

        // Render canvas
        await page.render({ canvasContext: ctx, viewport }).promise;

        // Render text layer (usando la nueva API)
        const textContent = await page.getTextContent();

        await pdfjsLib.renderTextLayer({
            textContentSource: textContent,  // ✅ CAMBIO: textContent → textContentSource
            container: textLayer,
            viewport: viewport,
            textDivs: []
        }).promise;

        // Highlight existing quotes
        this.highlightQuotes(textLayer);
    }

    highlightQuotes(textLayerDiv) {
        const textSpans = textLayerDiv.querySelectorAll('span');

        this.existingQuotes.forEach(quote => {
            const searchText = quote.text_fragment.trim();
            if (!searchText) return;

            textSpans.forEach(span => {
                if (span.textContent.includes(searchText) && span.textContent.trim().length > 5) {
                    span.classList.add('highlight-quote');
                    span.title = `Quote ID: ${quote.id}`;
                }
            });
        });
    }

    setupEventListeners() {
        console.log('🎯 Setting up text selection listener...');

        document.addEventListener('mouseup', (e) => {
            const selection = window.getSelection();

            // Validar que la selección está dentro del PDF
            if (!this.container.contains(selection.anchorNode)) {
                return;
            }

            const rawText = selection.toString();

            if (rawText.trim().length > 5) {
                // Limpiar texto
                const cleanText = rawText
                    .replace(/(\r\n|\n|\r)/gm, " ")
                    .replace(/\s+/g, " ")
                    .trim();

                // Detectar página
                let node = selection.anchorNode;
                if (node.nodeType === 3) {  // Text node
                    node = node.parentNode;
                }

                const pageContainer = node.closest('.page-container');
                const pageNumber = pageContainer
                    ? parseInt(pageContainer.dataset.pageNumber)
                    : 1;

                console.log(`✂️ Text selected on page ${pageNumber}:`, cleanText.substring(0, 50) + '...');

                this.currentSelection = { text: cleanText, page: pageNumber };

                // Emitir evento personalizado
                const event = new CustomEvent('textSelected', {
                    detail: this.currentSelection
                });
                document.dispatchEvent(event);
            }
        });

        console.log('✅ Text selection listener active');
    }

    scrollToPage(pageNumber) {
        const pageElement = document.getElementById(`page-${pageNumber}`);
        if (pageElement) {
            pageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    getCurrentSelection() {
        return this.currentSelection;
    }

    updateLoader(message) {
        if (this.loader) {
            const loaderText = this.loader.querySelector('span:last-child');
            if (loaderText) {
                loaderText.textContent = message;
            }
        }
    }

    showError(message) {
        if (this.loader) {
            this.loader.innerHTML = `
                <div class="text-error text-center p-8">
                    <h3 class="font-bold text-lg mb-2">Error cargando PDF</h3>
                    <p class="text-sm mb-4">${message}</p>
                    <button onclick="location.reload()" class="btn btn-primary btn-sm">
                        Reintentar
                    </button>
                </div>
            `;
        }
    }
}

// Exponer globalmente (en producción usa ES6 modules)
window.PDFViewer = PDFViewer;