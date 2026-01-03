// ui/extraction/static/scripts/components/pdf_viewer.js

class PDFViewer {
    constructor(options) {
        this.container = document.querySelector(options.containerSelector);
        this.loader = document.querySelector(options.loaderSelector);
        this.pdfUrl = options.pdfUrl;
        this.existingQuotes = options.existingQuotes || [];
        this.onSelectionChange = options.onSelectionChange || null;

        this.pdf = null;
        this.currentSelection = { text: '', page: 1 };
        this.renderedPages = new Set();  // ✅ Trackear páginas renderizadas

        console.log('🔧 PDFViewer constructor called');
        console.log('   Options:', options);
        console.log('   existingQuotes:', this.existingQuotes);
        console.log('   existingQuotes length:', this.existingQuotes.length);


        if (!this.container) {
            throw new Error('PDF container not found');
        }

        if (typeof pdfjsLib === 'undefined') {
            throw new Error('PDF.js library not loaded');
        }

        pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }

    async init() {
        console.log('📄 Initializing PDF Viewer...');

        try {
            const loadingTask = pdfjsLib.getDocument(this.pdfUrl);

            loadingTask.onProgress = (progress) => {
                if (progress.total > 0) {
                    const percent = Math.round((progress.loaded / progress.total) * 100);
                    this.updateLoader(`Cargando Documento... ${percent}%`);
                }
            };

            this.pdf = await loadingTask.promise;
            console.log(`✅ PDF loaded: ${this.pdf.numPages} pages`);

            // Configurar listeners ANTES de renderizar
            this.setupEventListeners();
            console.log('✅ Text selection listener active (before rendering)');

            if (this.loader) {
                this.loader.style.display = 'none';
            }

            // Renderizado progresivo
            console.log('🖼️ Starting progressive rendering...');

            // Renderizar primeras páginas
            const initialPages = Math.min(5, this.pdf.numPages);
            for (let pageNum = 1; pageNum <= initialPages; pageNum++) {
                await this.renderPage(pageNum);
            }

            console.log(`✅ Initial ${initialPages} pages rendered`);

            // Lazy loading del resto
            if (this.pdf.numPages > initialPages) {
                this.setupLazyLoading(initialPages);
            }

            console.log('✅ PDF Viewer ready');

        } catch (error) {
            console.error('❌ Error loading PDF:', error);
            this.showError(error.message);
            throw error;
        }
    }

    /**
     * ✅ Configurar lazy loading para páginas no renderizadas
     */
    setupLazyLoading(startPage) {
        console.log(`🔄 Setting up lazy loading for pages ${startPage + 1}-${this.pdf.numPages}`);

        // Crear observer para detectar cuando una página entra en viewport
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const pageNumber = parseInt(entry.target.dataset.pageNumber);

                        // Solo renderizar si no ha sido renderizada
                        if (!this.renderedPages.has(pageNumber)) {
                            console.log(`   🖼️ Lazy rendering page ${pageNumber}...`);
                            this.renderPage(pageNumber);
                        }
                    }
                });
            },
            {
                root: this.container,
                rootMargin: '500px',  // Cargar con 500px de anticipación
                threshold: 0.01
            }
        );

        // Crear placeholders para páginas no renderizadas
        for (let pageNum = startPage + 1; pageNum <= this.pdf.numPages; pageNum++) {
            this.createPagePlaceholder(pageNum, observer);
        }

        console.log(`✅ Lazy loading configured for ${this.pdf.numPages - startPage} pages`);
    }

    /**
     * ✅ Crear placeholder para una página
     */
    createPagePlaceholder(pageNumber, observer) {
        const placeholder = document.createElement('div');
        placeholder.className = 'page-container page-placeholder';
        placeholder.id = `page-${pageNumber}`;
        placeholder.dataset.pageNumber = pageNumber;

        // Estimar altura basada en las primeras páginas renderizadas
        const estimatedHeight = this.estimatePageHeight();

        placeholder.style.cssText = `
            position: relative;
            width: 100%;
            height: ${estimatedHeight}px;
            margin: 0 auto 20px auto;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            background-color: #f3f4f6;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        placeholder.innerHTML = `
            <div class="text-gray-400 text-center">
                <svg class="animate-spin h-8 w-8 mx-auto mb-2 opacity-50" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p class="text-sm">Página ${pageNumber}</p>
            </div>
        `;

        this.container.appendChild(placeholder);

        // Observar el placeholder
        observer.observe(placeholder);
    }

    /**
     * ✅ Estimar altura de página basándose en páginas ya renderizadas
     */
    estimatePageHeight() {
        // Buscar la primera página renderizada
        const firstPage = document.querySelector('.page-container:not(.page-placeholder)');

        if (firstPage) {
            return firstPage.offsetHeight;
        }

        // Fallback: altura estimada
        return 800;
    }

    // ui/extraction/static/scripts/components/pdf_viewer.js

    async renderPage(pageNumber) {
        if (this.renderedPages.has(pageNumber)) {
            console.log(`   ⏭️ Page ${pageNumber} already rendered, skipping`);
            return;
        }

        try {
            const page = await this.pdf.getPage(pageNumber);
            const scale = 1.3;
            const viewport = page.getViewport({ scale });

            // Buscar si existe placeholder
            let pageDiv = document.getElementById(`page-${pageNumber}`);

            if (pageDiv && pageDiv.classList.contains('page-placeholder')) {
                pageDiv.innerHTML = '';
                pageDiv.classList.remove('page-placeholder');
            } else if (!pageDiv) {
                pageDiv = document.createElement('div');
                pageDiv.id = `page-${pageNumber}`;
                pageDiv.dataset.pageNumber = pageNumber;
                this.container.appendChild(pageDiv);
            }

            pageDiv.className = 'page-container';
            pageDiv.style.cssText = `
            position: relative;
            width: ${viewport.width}px;
            height: ${viewport.height}px;
            margin: 0 auto 20px auto;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            background-color: white;
            display: block;
        `;

            // Canvas
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            canvas.style.display = 'block';

            // ✅ Text layer con --scale-factor
            const textLayer = document.createElement('div');
            textLayer.className = 'textLayer';
            textLayer.style.cssText = `
            position: absolute;
            text-align: initial;
            left: 0;
            top: 0;
            right: 0;
            bottom: 0;
            overflow: hidden;
            opacity: 1;
            line-height: 1;
            -webkit-text-size-adjust: none;
            -moz-text-size-adjust: none;
            text-size-adjust: none;
            forced-color-adjust: none;
            --scale-factor: ${scale};
        `;

            pageDiv.appendChild(canvas);
            pageDiv.appendChild(textLayer);

            // Render canvas
            await page.render({ canvasContext: ctx, viewport }).promise;

            // Render text layer
            const textContent = await page.getTextContent();

            const textLayerRender = pdfjsLib.renderTextLayer({
                textContentSource: textContent,
                container: textLayer,
                viewport: viewport,
                textDivs: [],
                enhanceTextSelection: true
            });

            await textLayerRender.promise;

            // Aplicar highlights
            this.highlightQuotesOnPage(textLayer, pageNumber);

            this.renderedPages.add(pageNumber);

            console.log(`   ✅ Page ${pageNumber} rendered`);

        } catch (error) {
            console.error(`   ❌ Error rendering page ${pageNumber}:`, error);
        }
    }

    /**
     * ✅ REEMPLAZAR: Aplicar highlights a quotes existentes en una página
     */
    highlightQuotesOnPage(textLayer, pageNumber) {
        const quotesOnPage = this.existingQuotes.filter(quote => {
            const quotePage = quote.location?.page || 0;
            return quotePage === pageNumber;
        });

        if (quotesOnPage.length === 0) {
            return;
        }

        console.log(`   🎨 Highlighting ${quotesOnPage.length} quotes on page ${pageNumber}`);

        quotesOnPage.forEach(quote => {
            const searchText = quote.text_fragment.trim();
            if (!searchText || searchText.length < 5) {
                return;
            }

            console.log(`      🔍 Searching for: "${searchText.substring(0, 50)}..."`);
            this.highlightTextInPage(textLayer, searchText, quote);
        });
    }

    highlightTextInPage(textLayer, searchText, quote) {
        const textSpans = Array.from(textLayer.querySelectorAll('span'));

        // 1. Construir texto completo con mapeo de caracteres
        let fullText = '';
        const charMap = [];

        textSpans.forEach((span, spanIndex) => {
            const spanText = span.textContent;

            for (let i = 0; i < spanText.length; i++) {
                charMap.push({
                    span: span,
                    spanIndex: spanIndex,
                    charIndex: i,
                    globalPos: fullText.length
                });

                fullText += spanText[i];
            }
        });

        // 2. Normalizar y buscar
        const normalizedFull = this.normalizeText(fullText);
        const normalizedSearch = this.normalizeText(searchText);

        let foundIndex = normalizedFull.indexOf(normalizedSearch);

        if (foundIndex === -1) {
            // Búsqueda parcial
            const searchLengths = [100, 50, 30];
            for (const len of searchLengths) {
                const shortSearch = normalizedSearch.substring(0, len);
                foundIndex = normalizedFull.indexOf(shortSearch);
                if (foundIndex !== -1) break;
            }

            if (foundIndex === -1) {
                console.log(`         ❌ Text not found`);
                return;
            }
        }

        // 3. Encontrar posición real
        const realStart = this.findRealPosition(fullText, normalizedFull, foundIndex);
        const realEnd = this.findRealPosition(fullText, normalizedFull, foundIndex + normalizedSearch.length);

        console.log(`         ✅ Found at ${foundIndex}, real position: ${realStart} to ${realEnd}`);

        // 4. Agrupar por span
        const spansToHighlight = new Map();

        for (let pos = realStart; pos < realEnd && pos < charMap.length; pos++) {
            const charInfo = charMap[pos];
            const spanIdx = charInfo.spanIndex;

            if (!spansToHighlight.has(spanIdx)) {
                spansToHighlight.set(spanIdx, {
                    span: charInfo.span,
                    firstCharIndex: charInfo.charIndex,
                    lastCharIndex: charInfo.charIndex
                });
            } else {
                const info = spansToHighlight.get(spanIdx);
                info.lastCharIndex = charInfo.charIndex;
            }
        }

        console.log(`         🎯 Highlighting ${spansToHighlight.size} spans`);

        // 5. Aplicar highlight con medición precisa
        spansToHighlight.forEach((info) => {
            const span = info.span;
            const spanText = span.textContent;
            const startChar = info.firstCharIndex;
            const endChar = info.lastCharIndex + 1;

            // Si cubre todo el span
            if (startChar === 0 && endChar >= spanText.length) {
                this.applyFullHighlight(span, quote);
                return;
            }

            // Si es parcial, calcular posición y ancho
            this.applyPartialHighlight(span, spanText, startChar, endChar, quote);
        });
    }

    /**
     * ✅ NUEVO: Aplicar highlight completo (todo el span)
     */
    applyFullHighlight(span, quote) {
        span.classList.add('highlight-quote');
        span.dataset.quoteId = quote.id;
        span.title = `Quote ID: ${quote.id}`;
        span.style.cursor = 'pointer';

        span.addEventListener('click', (e) => {
            e.stopPropagation();
            this.scrollToQuoteInSidebar(quote.id);
        }, { once: true });
    }

    /**
     * ✅ NUEVO: Aplicar highlight parcial usando ::before
     */
    applyPartialHighlight(span, spanText, startChar, endChar, quote) {
        // Obtener estilos del span
        const computedStyle = window.getComputedStyle(span);
        const fontSize = parseFloat(computedStyle.fontSize);
        const fontFamily = computedStyle.fontFamily;
        const transform = computedStyle.transform;

        // Extraer scaleX del transform
        let scaleX = 1;
        if (transform && transform !== 'none') {
            const matrix = transform.match(/matrix\(([^)]+)\)/);
            if (matrix) {
                const values = matrix[1].split(',').map(v => parseFloat(v.trim()));
                scaleX = values[0];
            }
        }

        // Medir anchos
        const textBefore = spanText.substring(0, startChar);
        const textHighlight = spanText.substring(startChar, endChar);

        const widthBefore = this.measureTextWithDOM(textBefore, fontSize, fontFamily, scaleX).width;
        const widthHighlight = this.measureTextWithDOM(textHighlight, fontSize, fontFamily, scaleX).width;
        const totalWidth = this.measureTextWithDOM(spanText, fontSize, fontFamily, scaleX).width;


        console.log(`            Partial highlight in span:`);
        console.log(`              Text: "${spanText}"`);
        console.log(`              Before: "${textBefore}" (${widthBefore.toFixed(2)}px)`);
        console.log(`              Highlight: "${textHighlight}" (${widthHighlight.toFixed(2)}px)`);
        console.log(`              Total width: ${totalWidth.toFixed(2)}px`);

        // Calcular porcentajes para el gradiente
        const startPercent = (widthBefore / totalWidth) * 100;
        const endPercent = ((widthBefore + widthHighlight) / totalWidth) * 100;

        console.log(`              Gradient: ${startPercent.toFixed(2)}% to ${endPercent.toFixed(2)}%`);

        // Aplicar gradiente como background
        span.classList.add('highlight-quote-partial');
        span.dataset.quoteId = quote.id;
        span.title = `Quote ID: ${quote.id}`;
        span.style.cursor = 'pointer';

        // ✅ Usar background-image con linear-gradient
        const gradient = `linear-gradient(to right, 
        transparent 0%, 
        transparent ${startPercent}%, 
        rgba(255, 215, 0, 0.4) ${startPercent}%, 
        rgba(255, 215, 0, 0.4) ${endPercent}%, 
        transparent ${endPercent}%, 
        transparent 100%)`;

        span.style.backgroundImage = gradient;
        span.style.backgroundSize = '100% 100%';
        span.style.backgroundRepeat = 'no-repeat';

        span.addEventListener('click', (e) => {
            e.stopPropagation();
            this.scrollToQuoteInSidebar(quote.id);
        }, { once: true });
    }

    /**
     * ✅ NUEVO: Medir ancho de texto usando Canvas
     */
    measureText(text, fontSize, fontFamily, scaleX = 1) {
        // Crear canvas temporal si no existe
        if (!this.measureCanvas) {
            this.measureCanvas = document.createElement('canvas');
            this.measureCtx = this.measureCanvas.getContext('2d');
        }

        // Configurar fuente
        this.measureCtx.font = `${fontSize}px ${fontFamily}`;

        // Medir texto
        const metrics = this.measureCtx.measureText(text);

        return {
            width: metrics.width * scaleX,
            height: fontSize
        };
    }
    measureTextWithDOM(text, fontSize, fontFamily, scaleX = 1) {
        // Crear span temporal para medir
        if (!this.measureSpan) {
            this.measureSpan = document.createElement('span');
            this.measureSpan.style.position = 'absolute';
            this.measureSpan.style.visibility = 'hidden';
            this.measureSpan.style.whiteSpace = 'pre';
            this.measureSpan.style.pointerEvents = 'none';
            document.body.appendChild(this.measureSpan);
        }

        // Aplicar estilos
        this.measureSpan.style.fontSize = `${fontSize}px`;
        this.measureSpan.style.fontFamily = fontFamily;
        this.measureSpan.style.transform = `scaleX(${scaleX})`;
        this.measureSpan.textContent = text;

        // Medir
        const rect = this.measureSpan.getBoundingClientRect();

        return {
            width: rect.width,
            height: rect.height
        };
    }

    /**
     * ✅ NUEVO: Aplicar highlight a un span completo
     */
    applyHighlightToSpan(span, quote) {
        span.classList.add('highlight-quote');
        span.dataset.quoteId = quote.id;
        span.title = `Quote ID: ${quote.id}`;
        span.style.cursor = 'pointer';

        span.addEventListener('click', (e) => {
            e.stopPropagation();
            this.scrollToQuoteInSidebar(quote.id);
        }, { once: true });
    }

    /**
     * ✅ NUEVO: Dividir span y aplicar highlight solo a la parte seleccionada
     */
    splitAndHighlightSpan(originalSpan, startChar, endChar, quote) {
        const fullText = originalSpan.textContent;

        // Dividir en 3 partes
        const beforeText = fullText.substring(0, startChar);
        const highlightText = fullText.substring(startChar, endChar);
        const afterText = fullText.substring(endChar);

        // Crear contenedor wrapper
        const wrapper = document.createElement('span');
        wrapper.style.position = 'relative';
        wrapper.style.display = 'inline';

        // Copiar estilos críticos del span original
        const computedStyle = window.getComputedStyle(originalSpan);
        wrapper.style.fontFamily = computedStyle.fontFamily;
        wrapper.style.fontSize = computedStyle.fontSize;
        wrapper.style.transform = computedStyle.transform;

        // Crear spans para cada parte
        if (beforeText) {
            const beforeSpan = this.createTextSpan(beforeText, originalSpan);
            wrapper.appendChild(beforeSpan);
        }

        if (highlightText) {
            const highlightSpan = this.createTextSpan(highlightText, originalSpan);
            this.applyHighlightToSpan(highlightSpan, quote);
            wrapper.appendChild(highlightSpan);
        }

        if (afterText) {
            const afterSpan = this.createTextSpan(afterText, originalSpan);
            wrapper.appendChild(afterSpan);
        }

        // Reemplazar span original con el wrapper
        originalSpan.replaceWith(wrapper);

        console.log(`            Split span: "${beforeText}" | "${highlightText}" | "${afterText}"`);
    }

    /**
     * ✅ NUEVO: Crear span de texto con estilos del original
     */
    createTextSpan(text, originalSpan) {
        const span = document.createElement('span');
        span.textContent = text;

        // Copiar atributos importantes
        const computedStyle = window.getComputedStyle(originalSpan);

        span.style.color = 'transparent'; // Para que el text layer funcione
        span.style.position = 'relative';
        span.style.whiteSpace = 'pre';
        span.style.cursor = 'text';

        return span;
    }

    /**
 * ✅ REEMPLAZAR: Normalización mejorada
 */
    normalizeText(text) {
        return text
            .replace(/[\r\n]+/g, ' ')           // Saltos de línea → espacio
            .replace(/\s+/g, ' ')               // Múltiples espacios → uno
            .replace(/\s*([.,!?;:)\]}>])\s*/g, '$1') // Quitar espacios después de puntuación de cierre
            .replace(/\s*([\[{(<])\s*/g, '$1')  // Quitar espacios antes de puntuación de apertura
            .replace(/\s*-\s*/g, '-')           // Quitar espacios alrededor de guiones
            .replace(/['']/g, "'")              // Normalizar apóstrofes
            .replace(/[""]/g, '"')              // Normalizar comillas
            .replace(/–/g, '-')                 // En dash
            .replace(/—/g, '-')                 // Em dash
            .replace(/…/g, '...')               // Ellipsis
            .normalize('NFD')                   // Normalizar Unicode
            .replace(/[\u0300-\u036f]/g, '')    // Remover acentos
            .trim()
            .toLowerCase();
    }

    /**
     * ✅ ACTUALIZAR: Mejor mapeo de posiciones
     */
    findRealPosition(originalText, normalizedText, normalizedPos) {
        if (normalizedPos === 0) return 0;
        if (normalizedPos >= normalizedText.length) return originalText.length;

        let realPos = 0;
        let normPos = 0;

        while (realPos < originalText.length && normPos < normalizedPos) {
            const char = originalText[realPos];

            // Si es whitespace en el original
            if (/\s/.test(char)) {
                realPos++;

                // Si en el normalizado hay espacio, avanzar
                if (normPos < normalizedText.length && normalizedText[normPos] === ' ') {
                    normPos++;
                }
                // Si no, seguir (espacios colapsados)
                continue;
            }

            // Si es puntuación que puede tener espacios removidos
            if (/[.,!?;:)\]}>'\-–—]/.test(char)) {
                realPos++;

                if (normPos < normalizedText.length) {
                    const normChar = normalizedText[normPos];

                    // Si el char normalizado coincide, avanzar
                    if (char.toLowerCase() === normChar ||
                        (char === '–' && normChar === '-') ||
                        (char === '—' && normChar === '-') ||
                        (char === "'" && normChar === "'") ||
                        (char === '"' && normChar === '"')) {
                        normPos++;
                    }
                }
                continue;
            }

            // Caracter normal
            const normChar = normalizedText[normPos];

            if (char.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() === normChar) {
                normPos++;
            }

            realPos++;
        }

        return realPos;
    }

    /**
     * ✅ AGREGAR ESTE MÉTODO: Scroll a una quote en el sidebar
     */
    scrollToQuoteInSidebar(quoteId) {
        console.log(`📍 Scrolling to quote ${quoteId} in sidebar`);

        const quoteCard = document.querySelector(`[data-quote-id="${quoteId}"]`);

        if (quoteCard) {
            quoteCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            // Animación de highlight temporal
            quoteCard.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
            setTimeout(() => {
                quoteCard.classList.remove('ring-2', 'ring-primary', 'ring-offset-2');
            }, 2000);
        }
    }

    /**
     * ✅ AGREGAR ESTE MÉTODO: Re-aplicar highlights en una página específica
     */
    rehighlightPage(pageNumber) {
        console.log(`🎨 Re-highlighting page ${pageNumber}...`);

        const pageDiv = document.getElementById(`page-${pageNumber}`);

        if (!pageDiv) {
            console.warn(`   ⚠️ Page ${pageNumber} not rendered yet`);
            return;
        }

        const textLayer = pageDiv.querySelector('.textLayer');

        if (!textLayer) {
            console.warn(`   ⚠️ Text layer not found on page ${pageNumber}`);
            return;
        }

        // Re-aplicar highlights
        this.highlightQuotesOnPage(textLayer, pageNumber);

        console.log(`   ✅ Page ${pageNumber} re-highlighted`);
    }

    /**
     * ✅ AGREGAR ESTE MÉTODO: Refrescar todos los highlights
     */
    refreshAllHighlights() {
        console.log('🔄 Refreshing all highlights...');

        this.renderedPages.forEach(pageNumber => {
            const pageDiv = document.getElementById(`page-${pageNumber}`);
            if (!pageDiv) return;

            const textLayer = pageDiv.querySelector('.textLayer');
            if (!textLayer) return;

            // Remover highlights existentes
            const highlightedSpans = textLayer.querySelectorAll('.highlight-quote');
            highlightedSpans.forEach(span => {
                span.classList.remove('highlight-quote');
                delete span.dataset.quoteId;
                span.title = '';
                span.style.cursor = '';
            });

            // Re-aplicar
            this.highlightQuotesOnPage(textLayer, pageNumber);
        });

        console.log('✅ All highlights refreshed');
    }

    setupEventListeners() {
        console.log('🎯 Setting up text selection listener...');

        document.addEventListener('mouseup', (e) => {
            const selection = window.getSelection();

            if (!this.container.contains(selection.anchorNode)) {
                return;
            }

            const rawText = selection.toString();

            if (rawText.trim().length > 5) {
                const cleanText = rawText
                    .replace(/(\r\n|\n|\r)/gm, " ")
                    .replace(/\s+/g, " ")
                    .trim();

                let node = selection.anchorNode;
                if (node.nodeType === 3) {
                    node = node.parentNode;
                }

                const pageContainer = node.closest('.page-container');
                const pageNumber = pageContainer
                    ? parseInt(pageContainer.dataset.pageNumber)
                    : 1;

                console.log(`✂️ Text selected on page ${pageNumber}:`, cleanText.substring(0, 50) + '...');

                this.currentSelection = { text: cleanText, page: pageNumber };

                // Llamar al callback si existe
                if (this.onSelectionChange) {
                    this.onSelectionChange(this.currentSelection);
                }
            }
        });

        console.log('✅ Text selection listener active');
    }

    styleTextSpans(textLayerDiv) {
        const textSpans = textLayerDiv.querySelectorAll('span');

        textSpans.forEach(span => {
            span.style.cssText = `
                color: transparent;
                position: absolute;
                white-space: pre;
                cursor: text;
                transform-origin: 0% 0%;
            `;
        });
    }

    scrollToPage(pageNumber) {
        const pageElement = document.getElementById(`page-${pageNumber}`);
        if (pageElement) {
            pageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            console.log(`✅ Scrolled to page ${pageNumber}`);
        }
    }

    scrollToQuoteInSidebar(quoteId) {
        console.log(`📍 Scrolling to quote ${quoteId} in sidebar`);

        const quoteCard = document.querySelector(`[data-quote-id="${quoteId}"]`);

        if (quoteCard) {
            quoteCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            // Animación de highlight temporal
            quoteCard.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
            setTimeout(() => {
                quoteCard.classList.remove('ring-2', 'ring-primary', 'ring-offset-2');
            }, 2000);
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
                    <svg class="w-16 h-16 mx-auto mb-4 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
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

window.PDFViewer = PDFViewer;