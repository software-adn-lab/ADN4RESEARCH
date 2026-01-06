/**
 * Paper Workspace - Con carga asíncrona de PDF.js
 */

class PaperWorkspace {
    constructor(config) {
        this.config = config;
        this.pdfViewer = null;
        this.currentSelection = null;
        this.modal = document.getElementById('quote_modal');
        this.form = document.getElementById('quote-form');

        console.log('🔧 PaperWorkspace constructor');
    }

    async init() {
        console.log('🚀 Initializing workspace');

        try {
            // ✅ 1. Configurar listeners PRIMERO (antes de cargar PDF)
            this.setupEventListeners();
            console.log('✅ Event listeners ready');

            // ✅ 2. Luego cargar PDF (no bloquea la creación de quotes)
            await this.waitForPDFJS();
            await this.initPDF();

            console.log('✅ Workspace ready');
        } catch (error) {
            console.error('❌ Init failed:', error);
            this.showError(error.message);
        }
    }

    /**
     * ✅ NUEVO: Esperar a que PDF.js se cargue
     */
    async waitForPDFJS() {
        console.log('⏳ Waiting for PDF.js to load...');

        return new Promise((resolve, reject) => {
            // Si ya está cargado
            if (typeof pdfjsLib !== 'undefined') {
                console.log('✅ PDF.js already loaded');
                resolve();
                return;
            }

            // Esperar hasta 10 segundos
            let attempts = 0;
            const maxAttempts = 100; // 100 * 100ms = 10 segundos

            const checkInterval = setInterval(() => {
                attempts++;

                if (typeof pdfjsLib !== 'undefined') {
                    console.log(`✅ PDF.js loaded after ${attempts * 100}ms`);
                    clearInterval(checkInterval);
                    resolve();
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    reject(new Error('PDF.js no se cargó después de 10 segundos'));
                }
            }, 100);
        });
    }

    async initPDF() {
        const container = document.getElementById('pdf-viewer-container');
        const loader = document.getElementById('pdf-loader');
        const SCALE = 1.3; // Definimos la escala globalmente para consistencia

        console.log('📄 Loading PDF from:', this.config.pdfUrl);

        try {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

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

            this.pdfViewer = await loadingTask.promise;
            console.log(`✅ PDF loaded: ${this.pdfViewer.numPages} pages`);

            if (loader) loader.style.display = 'none';

            const firstPage = await this.pdfViewer.getPage(1);
            const viewport = firstPage.getViewport({ scale: SCALE });
            const pageWidth = viewport.width;
            const pageHeight = viewport.height;

            console.log(`📏 Base page dimensions: ${pageWidth}x${pageHeight}`);

            // 1. CALCULAR PÁGINAS PRIORITARIAS (Quotes ± 5)
            const priorityPages = new Set();
            if (this.pdfViewer.numPages > 10) {
                for (let i = 1; i <= 10; i++) {
                    priorityPages.add(i);
                }
            } else {
                for (let i = 1; i <= this.pdfViewer.numPages; i++) {
                    priorityPages.add(i);
                }
            }
            if (this.config.existingQuotes && Array.isArray(this.config.existingQuotes)) {
                this.config.existingQuotes.forEach(quote => {
                    const p = quote.location?.page || 0;
                    for (let i = p - 5; i <= p + 5; i++) {
                        if (i >= 1 && i <= this.pdfViewer.numPages) {
                            priorityPages.add(i);
                        }
                    }
                });
            }

            // 2. CREAR PLACEHOLDERS CON TAMAÑO FIJO Y SKELETON
            const pagePlaceholders = [];

            for (let i = 1; i <= this.pdfViewer.numPages; i++) {
                const placeholder = document.createElement('div');
                placeholder.id = `page-placeholder-${i}`;
                placeholder.className = 'pdf-page-placeholder relative mb-5'; // mb-5 para separación

                // ✅ AQUI LA MAGIA: Forzamos el tamaño exacto desde el inicio
                placeholder.style.width = `${pageWidth}px`;
                placeholder.style.height = `${pageHeight}px`;
                placeholder.style.margin = '0 auto 20px'; // Centrado
                placeholder.style.backgroundColor = 'white';
                placeholder.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';

                // ✅ Insertamos tu Skeleton
                // Usamos w-full h-full para que llene el contenedor de tamaño fijo
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

                container.appendChild(placeholder);
                pagePlaceholders[i] = placeholder;
            }

            // 3. SEPARAR EN COLAS
            const highPriorityQueue = [];
            const lowPriorityQueue = [];

            for (let i = 1; i <= this.pdfViewer.numPages; i++) {
                if (priorityPages.has(i)) {
                    highPriorityQueue.push(i);
                } else {
                    lowPriorityQueue.push(i);
                }
            }

            // 4. RENDERIZAR
            // Pasamos SCALE a renderPage para asegurar consistencia
            console.log('🚀 Starting Priority Render...');
            for (const pageNum of highPriorityQueue) {
                await this.renderPage(pageNum, pagePlaceholders[pageNum], SCALE);
            }

            console.log('💤 Starting Background Render...');
            for (const pageNum of lowPriorityQueue) {
                await this.renderPage(pageNum, pagePlaceholders[pageNum], SCALE);
                if (pageNum % 5 === 0) await new Promise(r => setTimeout(r, 0));
            }

            console.log('✅ All pages rendered');

        } catch (error) {
            console.error('❌ Error loading PDF:', error);
            this.showError(error.message);
        }
    }

    async renderPage(pageNum, container, scale = 1.3) { // Recibe scale
        try {
            const page = await this.pdfViewer.getPage(pageNum);
            // Usamos la escala que pasamos desde initPDF
            const viewport = page.getViewport({ scale });

            const pageDiv = document.createElement('div');
            pageDiv.className = 'page-container';
            pageDiv.dataset.pageNumber = pageNum;

            // El pageDiv interno ocupa el 100% del placeholder
            pageDiv.style.cssText = `
            width: 100%;
            height: 100%;
            position: relative;
        `;

            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const ctx = canvas.getContext('2d');

            const textLayer = document.createElement('div');
            textLayer.className = 'textLayer';
            textLayer.style.cssText = `
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            bottom: 0;
            overflow: hidden;
            opacity: 0.25;
            line-height: 1.0;
            --scale-factor: ${scale};
        `;

            pageDiv.appendChild(canvas);
            pageDiv.appendChild(textLayer);

            // ✅ LIMPIEZA: Esto borra el Skeleton HTML automáticamente
            container.innerHTML = '';
            // Ya no necesitamos setear estilos al container, porque ya se los dimos en initPDF
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

    /**
     * ✅ NUEVO: Aplicar highlights a las quotes existentes en una página
     */
    highlightQuotesOnPage(textLayer, pageNumber) {
        if (!this.config.existingQuotes || this.config.existingQuotes.length === 0) {
            return;
        }

        // Filtrar quotes de esta página
        const quotesOnPage = this.config.existingQuotes.filter(quote => {
            const quotePage = quote.location?.page || 0;
            return quotePage === pageNumber;
        });

        if (quotesOnPage.length === 0) {
            return;
        }

        console.log(`   🎨 Highlighting ${quotesOnPage.length} quotes on page ${pageNumber}`);

        quotesOnPage.forEach(quote => {
            this.highlightTextInLayer(textLayer, quote.text_fragment, quote);
        });
    }

    /**
     * ✅ NUEVO: Buscar y destacar texto en el text layer
     */
    /**
     * ✅ CORREGIDO: Buscar texto ignorando problemas de espaciado
     */
    highlightTextInLayer(textLayer, searchText, quote) {
        const textSpans = Array.from(textLayer.querySelectorAll('span'));
        if (textSpans.length === 0) return;

        // 1. Normalización ESTRICTA (quitamos todos los espacios) para la búsqueda
        // Esto soluciona el problema de "HolaMundo" vs "Hola Mundo"
        const searchStrict = this.normalizeStrict(searchText);

        if (!searchStrict) return;

        // 2. Construir mapa de texto y mapeo de índices
        let fullTextStrict = '';
        const spanMap = [];

        textSpans.forEach((span, index) => {
            const spanTextStrict = this.normalizeStrict(span.textContent);

            // Guardamos dónde empieza este span en la cadena gigante "sin espacios"
            spanMap.push({
                index: index,
                start: fullTextStrict.length,
                length: spanTextStrict.length,
                element: span
            });

            fullTextStrict += spanTextStrict;
        });

        // 3. Buscar coincidencia exacta en la cadena sin espacios
        let foundIndex = fullTextStrict.indexOf(searchStrict);

        // Fallback: Intentar con los primeros 50 caracteres si falla (por si la quote es muy larga y corta mal)
        if (foundIndex === -1 && searchStrict.length > 50) {
            const shortSearch = searchStrict.substring(0, 50);
            foundIndex = fullTextStrict.indexOf(shortSearch);
        }

        if (foundIndex === -1) {
            console.warn(`⚠️ Text not found (strict match) for quote ${quote.id}`);
            // Opcional: Imprimir para debug
            // console.log('Search:', searchStrict.substring(0, 20) + '...');
            // console.log('Doc:', fullTextStrict.substring(0, 50) + '...');
            return;
        }

        // 4. Calcular el índice final de la coincidencia
        const endIndex = foundIndex + searchStrict.length;

        // 5. Encontrar qué spans cubren este rango (startSpanIdx y endSpanIdx)
        let startSpanIdx = -1;
        let endSpanIdx = -1;

        for (const map of spanMap) {
            // El span contiene el inicio de la búsqueda?
            const spanEnd = map.start + map.length;

            // Si no hemos encontrado el inicio, y este span termina DESPUÉS de donde empieza la búsqueda
            if (startSpanIdx === -1 && spanEnd > foundIndex) {
                startSpanIdx = map.index;
            }

            // Si ya encontramos el inicio, buscamos donde termina
            // Este span empieza ANTES de que termine la búsqueda
            if (startSpanIdx !== -1 && map.start < endIndex) {
                endSpanIdx = map.index;
            }
        }

        if (startSpanIdx === -1 || endSpanIdx === -1) return;

        // 6. Aplicar highlight
        console.log(`✅ Highlighted quote ${quote.id} (spans ${startSpanIdx} to ${endSpanIdx})`);

        for (let i = startSpanIdx; i <= endSpanIdx; i++) {
            const span = textSpans[i];

            // Evitar doble highlight si ya tiene clase
            if (!span.classList.contains('highlight-quote')) {
                span.classList.add('highlight-quote');
                span.dataset.quoteId = quote.id;

                // Estilos directos
                span.style.mixBlendMode = 'multiply'; // Ayuda a que se lea mejor el texto negro
                span.title = `Quote #${quote.id}`;

                span.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.scrollToQuoteInSidebar(quote.id);
                });
            }
        }
    }

    /**
     * ✅ NUEVO: Normalizar eliminando TODOS los espacios y caracteres invisibles
     * Esto es crucial para pdf.js donde los espacios son posicionales, no caracteres.
     */
    normalizeStrict(text) {
        if (!text) return '';
        return text
            .replace(/\s+/g, '')       // Quita espacios, tabs, saltos de línea
            .replace(/\u00A0/g, '')    // Quita Non-breaking spaces (&nbsp;)
            .toLowerCase();
    }

    /**
     * ✅ NUEVO: Scroll a una quote en el sidebar
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

    setupEventListeners() {
        console.log('🎯 Setting up event listeners');

        // ✅ Listener global de selección (funciona incluso sin PDF cargado)
        document.addEventListener('mouseup', (e) => {
            const selection = window.getSelection();
            const text = selection.toString().trim();

            if (text.length < 10) return;

            // Detectar página (si el PDF ya está renderizado)
            let pageNumber = 1;  // Default
            let node = selection.anchorNode;

            if (node && node.nodeType === 3) {
                node = node.parentNode;
            }

            if (node) {
                const pageContainer = node.closest('.page-container');
                if (pageContainer) {
                    pageNumber = parseInt(pageContainer.dataset.pageNumber) || 1;
                }
            }

            console.log(`✂️ Text selected (${text.length} chars) on page ${pageNumber}`);
            this.showQuoteModal(text, pageNumber);
        });

        // Submit formulario
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createQuote();
            });
        } else {
            console.error('❌ Quote form not found!');
        }
    }

    showQuoteModal(text, page) {
        this.currentSelection = { text, page };

        // ✅ Validar que los elementos existan
        const textArea = document.getElementById('selected-text');
        const pageInfo = document.getElementById('page-info');

        if (!textArea) {
            console.error('❌ Element #selected-text not found in modal');
            alert('Error: Modal no configurado correctamente');
            return;
        }

        if (!this.modal) {
            console.error('❌ Modal #quote_modal not found');
            alert('Error: Modal no encontrado');
            return;
        }

        // Actualizar valores
        textArea.value = text;

        if (pageInfo) {
            pageInfo.textContent = `Página ${page}`;
        }

        // Reset tags
        this.form.querySelectorAll('input[name="tags"]').forEach(cb => {
            cb.checked = false;
        });

        // Abrir modal
        this.modal.showModal();

        console.log('✅ Modal opened with text from page', page);
    }

    async createQuote() {
        const formData = new FormData(this.form);
        const tags = formData.getAll('tags').map(id => parseInt(id));

        console.log('📤 Creating quote...');

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
                console.log('✅ Quote created successfully:', responseData.quote);

                // Cerrar modal
                this.modal.close();

                // Agregar quote al sidebar
                this.addQuoteToSidebar(responseData.quote);

                // ✅ Actualizar tags obligatorios y porcentaje
                this.updateMandatoryTagsUI(responseData.quote.tags);

                // Mostrar notificación
                this.showSuccessNotification('Quote creada exitosamente');

                if (!this.config.existingQuotes) {
                    this.config.existingQuotes = [];
                }
                this.config.existingQuotes.push(responseData.quote);

                // ✅ NUEVO 2: Pintar inmediatamente en el PDF
                this.highlightNewQuote(responseData.quote);

                // ✅ NUEVO 3: Limpiar la selección azul del navegador para ver el highlight amarillo
                window.getSelection().removeAllRanges();

            } else {
                console.error('❌ Server error:', responseData);
                alert(`Error al crear quote:\n${responseData.error}`);
            }
        } catch (error) {
            console.error('❌ Network error:', error);
            alert('Error de red: ' + error.message);
        }
    }
    /**
 * ✅ NUEVO: Busca la página en el DOM y pinta la nueva quote inmediatamente
 */
    highlightNewQuote(quote) {
        const pageNum = quote.location.page;

        // Buscar el contenedor de la página usando el data-attribute que definimos en renderPage
        // Asumiendo que usaste: pageDiv.dataset.pageNumber = pageNum;
        const pageContainer = document.querySelector(`.page-container[data-page-number="${pageNum}"]`);

        if (!pageContainer) {
            console.warn(`⚠️ Page container for page ${pageNum} not found in DOM`);
            return;
        }

        const textLayer = pageContainer.querySelector('.textLayer');

        if (!textLayer) {
            console.warn('⚠️ Text layer not found');
            return;
        }

        console.log(`🎨 Immediately highlighting new quote ${quote.id} on page ${pageNum}`);

        // Reutilizamos la lógica robusta de pintado que arreglamos antes
        this.highlightTextInLayer(textLayer, quote.text_fragment, quote);
    }

    /**
     * ✅ ACTUALIZADO: Actualizar UI de tags obligatorios
     */
    updateMandatoryTagsUI(quoteTags) {
        console.log('🔄 Updating mandatory tags UI...');

        // 1. Actualizar badges de tags individuales
        quoteTags.forEach(tag => {
            const badge = document.querySelector(`[data-tag-id="${tag.id}"]`);

            if (badge && !badge.classList.contains('badge-success')) {
                // Cambiar a verde con checkmark
                badge.classList.remove('badge-ghost');
                badge.classList.add('badge-success', 'text-white');
                badge.style.opacity = '1';
                badge.title = '✅ Tag cubierto';

                // Agregar checkmark si no existe
                if (!badge.querySelector('svg')) {
                    const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    checkmark.setAttribute('class', 'inline-block w-3 h-3 stroke-current');
                    checkmark.setAttribute('fill', 'none');
                    checkmark.setAttribute('viewBox', '0 0 24 24');
                    checkmark.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>';

                    badge.insertBefore(checkmark, badge.firstChild);
                    badge.insertBefore(document.createTextNode(' '), badge.firstChild.nextSibling);
                }

                console.log(`   ✅ Tag ${tag.name} marked as covered`);
            }
        });

        // 2. ✅ Recalcular y actualizar porcentaje
        this.updateCoveragePercentage();

        // 3. ✅ Actualizar mensaje de tags faltantes
        this.updateMissingTagsAlert();
    }

    /**
 * ✅ ACTUALIZADO: Actualizar el porcentaje de cobertura y progress bar
 */
    updateCoveragePercentage() {
        // Contar tags obligatorios totales
        const allMandatoryBadges = document.querySelectorAll('[data-tag-id]');
        const totalMandatory = allMandatoryBadges.length;

        if (totalMandatory === 0) {
            console.log('   ℹ️ No mandatory tags to track');
            return;
        }

        // Contar tags cubiertos (verdes)
        const coveredBadges = document.querySelectorAll('[data-tag-id].badge-success');
        const coveredCount = coveredBadges.length;

        // Calcular porcentaje
        const percentage = Math.round((coveredCount / totalMandatory) * 100);

        console.log(`   📊 Coverage: ${coveredCount}/${totalMandatory} = ${percentage}%`);

        // 2. ✅ Actualizar progress bar
        const progressContainer = document.querySelector('#coverage-progress-container');
        if (progressContainer) {
            const progressBar = progressContainer.querySelector('.progress');
            if (progressBar) {
                progressBar.value = percentage;

                // Cambiar color del progress bar según porcentaje
                progressBar.classList.remove('progress-success', 'progress-warning', 'progress-error');

                if (percentage === 100) {
                    progressBar.classList.add('progress-success');
                } else if (percentage >= 50) {
                    progressBar.classList.add('progress-warning');
                } else {
                    progressBar.classList.add('progress-error');
                }

                console.log(`   ✅ Progress bar updated to ${percentage}%`);
            }

            const percentageBadge = progressContainer.querySelector('.badge');
            if (percentageBadge) {
                percentageBadge.textContent = `${percentage}%`;

                // Cambiar color según progreso
                percentageBadge.classList.remove('badge-warning', 'badge-success', 'badge-error');

                if (percentage === 100) {
                    percentageBadge.classList.add('badge-success');
                } else if (percentage >= 50) {
                    percentageBadge.classList.add('badge-warning');
                } else {
                    percentageBadge.classList.add('badge-error');
                }

                console.log(`   ✅ Badge updated to ${percentage}%`);
            }
        }

        // 4. ✅ Actualizar radial progress (si existe - para versiones futuras)
        const radialProgress = document.querySelector('.radial-progress');
        if (radialProgress) {
            radialProgress.style.setProperty('--value', percentage);
            radialProgress.textContent = `${percentage}%`;
            console.log(`   ✅ Radial progress updated`);
        }
    }

    /**
     * ✅ NUEVO: Actualizar alert de tags faltantes
     */
    updateMissingTagsAlert() {
        // Obtener tags faltantes
        const allMandatoryBadges = document.querySelectorAll('[data-tag-id]');
        const missingTags = [];

        allMandatoryBadges.forEach(badge => {
            if (!badge.classList.contains('badge-success')) {
                const tagName = badge.textContent.trim();
                const tagId = badge.dataset.tagId;
                missingTags.push({ id: tagId, name: tagName });
            }
        });

        console.log(`   ⚠️ Missing tags: ${missingTags.length}`);

        // Buscar el contenedor de alertas
        const alertContainer = document.querySelector('#mandatory_tags');
        if (!alertContainer) return;

        // Remover alerta existente
        const existingAlert = alertContainer.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        // Crear nueva alerta
        if (missingTags.length === 0) {
            // ✅ Todos cubiertos
            const successAlert = document.createElement('div');
            successAlert.className = 'alert alert-success mt-3 py-2 text-xs';
            successAlert.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Todos los tags obligatorios han sido cubiertos</span>
        `;
            alertContainer.appendChild(successAlert);

        } else {
            // ⚠️ Faltan tags
            const warningAlert = document.createElement('div');
            warningAlert.className = 'alert alert-warning mt-3 py-2 text-xs';

            const tagsHtml = missingTags.map(tag =>
                `<span class="badge badge-xs badge-ghost">${tag.name}</span>`
            ).join(' ');

            warningAlert.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div class="flex-1">
                <span class="font-semibold">Faltan ${missingTags.length} tag(s):</span>
                <div class="flex flex-wrap gap-1 mt-1">
                    ${tagsHtml}
                </div>
            </div>
        `;
            alertContainer.appendChild(warningAlert);
        }
    }

    /**
     * ✅ NUEVO: Agregar quote al sidebar dinámicamente
     */
    addQuoteToSidebar(quote) {
        const quotesList = document.getElementById('quotes-list-container');

        if (!quotesList) {
            console.warn('⚠️ Quotes list not found, reloading page');
            location.reload();
            return;
        }

        // Remover estado vacío si existe
        const emptyState = quotesList.querySelector('#empty-quotes-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Crear elemento de quote
        const quoteCard = document.createElement('div');
        quoteCard.className = 'card bg-white border hover:shadow-md transition group quote-card';
        quoteCard.dataset.quoteId = quote.id;
        quoteCard.dataset.page = quote.location.page || 1;

        // Construir HTML de tags
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
            <div class="flex flex-wrap gap-1 mt-2">
                ${tagsHtml}
            </div>
        </div>
    `;

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

    /**
     * ✅ NUEVO: Actualizar estado de tags obligatorios
     */
    updateMandatoryTagsStatus(quoteTags) {
        // Buscar los badges de tags obligatorios
        const tagBadges = document.querySelectorAll('[data-tag-id]');

        quoteTags.forEach(tag => {
            const badge = document.querySelector(`[data-tag-id="${tag.id}"]`);

            if (badge && !badge.classList.contains('badge-success')) {
                // Cambiar a verde con checkmark
                badge.classList.remove('badge-ghost');
                badge.classList.add('badge-success', 'text-white');
                badge.style.opacity = '1';
                badge.title = '✅ Tag cubierto';

                // Agregar checkmark si no existe
                if (!badge.querySelector('svg')) {
                    const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    checkmark.setAttribute('class', 'inline-block w-3 h-3 stroke-current');
                    checkmark.setAttribute('fill', 'none');
                    checkmark.setAttribute('viewBox', '0 0 24 24');
                    checkmark.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>';

                    badge.insertBefore(checkmark, badge.firstChild);
                }
            }
        });

        console.log('✅ Mandatory tags status updated');
    }

    /**
     * ✅ NUEVO: Mostrar notificación de éxito
     */
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

    /**
 * ✅ NUEVO: Eliminar visualmente una quote del PDF sin recargar
 */
    removeQuoteHighlight(quoteId) {
        // 1. Convertir ID a string/int para asegurar comparación correcta
        const id = parseInt(quoteId);

        // 2. Buscar todos los spans que pertenecen a esta quote en TODO el documento
        // (Nota: busca en todas las páginas renderizadas actualmente)
        const highlightedSpans = document.querySelectorAll(`.highlight-quote[data-quote-id="${id}"]`);

        if (highlightedSpans.length === 0) {
            console.warn(`⚠️ No visual highlights found for quote ${id} (maybe page not rendered)`);
        } else {
            console.log(`🧹 Removing highlight for quote ${id} from ${highlightedSpans.length} spans`);

            highlightedSpans.forEach(span => {
                // Remover clase y estilos visuales
                span.classList.remove('highlight-quote');
                span.style.backgroundColor = '';
                span.style.cursor = '';
                span.style.mixBlendMode = '';
                span.title = '';

                // Limpiar dataset
                delete span.dataset.quoteId;

                // Clonar nodo para eliminar TODOS los event listeners (el click para scroll)
                const newSpan = span.cloneNode(true);
                span.parentNode.replaceChild(newSpan, span);
            });
        }

        // 3. Actualizar el array local existingQuotes
        // Esto es importante por si el usuario hace scroll, desmonta la página y vuelve a montarla
        if (this.config.existingQuotes) {
            this.config.existingQuotes = this.config.existingQuotes.filter(q => q.id !== id);
            console.log(`✅ Quote ${id} removed from internal memory`);
        }
    }

    updateLoader(message) {
        const loader = document.getElementById('pdf-loader');
        if (loader) {
            const text = loader.querySelector('span:last-child');
            if (text) text.textContent = message;
        }
    }

    showError(message) {
        const loader = document.getElementById('pdf-loader');
        if (loader) {
            loader.innerHTML = `
                <div class="text-center p-8">
                    <svg class="w-16 h-16 mx-auto mb-4 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <h3 class="font-bold text-lg mb-2 text-error">Error cargando PDF</h3>
                    <p class="text-sm mb-4 text-gray-600">${message}</p>
                    <button onclick="location.reload()" class="btn btn-primary btn-sm">
                        Reintentar
                    </button>
                </div>
            `;
        }
    }
}

// Funciones globales
window.scrollToQuote = function (quoteId, page) {
    const pageEl = document.querySelector(`[data-page-number="${page}"]`);
    if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
};

window.deleteQuote = async function (quoteId) {
    if (!confirm('¿Eliminar esta extracción?')) return;

    const url = window.PAPER_CONFIG.quoteDeleteUrlTemplate.replace('{id}', quoteId);

    try {
        const response = await fetch(url, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': window.PAPER_CONFIG.csrfToken }
        });

        if (response.ok) {
            location.reload();
        } else {
            alert('Error al eliminar');
        }
    } catch (error) {
        console.error(error);
        alert('Error de red');
    }
};

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    console.log('📱 DOM loaded');

    if (!window.PAPER_CONFIG) {
        console.error('❌ PAPER_CONFIG not found!');
        alert('Error: Configuración no encontrada');
        return;
    }

    const workspace = new PaperWorkspace(window.PAPER_CONFIG);
    workspace.init();
});