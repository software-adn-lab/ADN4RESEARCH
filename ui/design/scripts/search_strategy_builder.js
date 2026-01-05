document.addEventListener('DOMContentLoaded', () => {
    // Referencias
    const termsPool = document.getElementById('terms-pool');
    const strategyCanvas = document.getElementById('strategy-canvas');
    const exclusionsZone = document.getElementById('exclusions-zone');
    const addGroupBtn = document.getElementById('add-group-btn');
    const searchBtn = document.getElementById('search-studies-btn');
    const emptyMsg = document.getElementById('empty-canvas-msg');
    const livePreview = document.getElementById('live-string-preview');

    // Manual Exclusion Inputs
    const manualExclInput = document.getElementById('manual-exclusion-input');
    const manualExclBtn = document.getElementById('add-manual-exclusion-btn');

    let draggedData = null;

    init();

    function init() {
        setupDragEvents();

        // Portal loader to body to ensure it covers everything
        const loader = document.getElementById('full-screen-loader');
        if (loader) {
            document.body.appendChild(loader);
        }

        if (typeof INITIAL_DATA !== 'undefined' && INITIAL_DATA.main_terms) {
            loadFromJSON(INITIAL_DATA);
        } else {
            // Si es nuevo, agregamos un grupo vacío por defecto para UX
            createNewGroup();
        }

        addGroupBtn.addEventListener('click', () => createNewGroup());
        searchBtn.addEventListener('click', saveAndSearch);

        // Manual Exclusion Events
        manualExclBtn.addEventListener('click', addManualExclusion);
        manualExclInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault(); // Evitar submit del form si lo hubiera
                addManualExclusion();
            }
        });

        // Actualizar preview inicial
        updateStringPreview();
    }

    // ==========================================
    // LÓGICA DE ACTUALIZACIÓN EN TIEMPO REAL
    // ==========================================
    function updateStringPreview() {
        const data = collectData();

        if (data.main_terms.length === 0) {
            livePreview.textContent = '(Add at least one Main Term to generate string)';
            livePreview.classList.add('text-base-content/50');
            livePreview.classList.remove('text-primary');
            return;
        }

        // Reconstrucción lógica Booleana (Espejo del Python)
        const groups = data.main_terms.map(group => {
            const terms = [`"${group.term}"`, ...group.synonyms.map(s => `"${s}"`)];
            return `(${terms.join(' OR ')})`;
        });

        let finalString = groups.join(' AND ');

        if (data.exclusions.length > 0) {
            const notTerms = data.exclusions.map(e => `"${e}"`).join(' OR ');
            finalString += ` AND NOT (${notTerms})`;
        }

        livePreview.textContent = finalString;
        livePreview.classList.remove('text-base-content/50');
        livePreview.classList.add('text-primary');
    }

    // ==========================================
    // LÓGICA DRAG & DROP
    // ==========================================
    function setupDragEvents() {
        const chips = document.querySelectorAll('.term-chip');
        chips.forEach(chip => {
            chip.addEventListener('dragstart', handleDragStart);
            chip.addEventListener('dragend', handleDragEnd);
        });
        setupDropZone(exclusionsZone, 'exclusion');
    }

    function handleDragStart(e) {
        this.classList.add('opacity-50');
        draggedData = {
            term: this.dataset.term,
            synonyms: this.dataset.synonyms
        };
        e.dataTransfer.effectAllowed = 'copy';
        e.dataTransfer.setData('text/plain', JSON.stringify(draggedData));
    }

    function handleDragEnd(e) {
        this.classList.remove('opacity-50');
        draggedData = null;
        document.querySelectorAll('.drop-active').forEach(el => {
            el.classList.remove('border-primary', 'bg-primary/5', 'drop-active', 'border-dashed');
        });
    }

    function setupDropZone(element, type) {
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            element.classList.add('border-primary', 'bg-primary/5', 'drop-active');
        });

        element.addEventListener('dragleave', (e) => {
            element.classList.remove('border-primary', 'bg-primary/5', 'drop-active');
        });

        element.addEventListener('drop', (e) => {
            e.preventDefault();
            element.classList.remove('border-primary', 'bg-primary/5', 'drop-active');

            // CORRECCIÓN: Parseo seguro del JSON
            let data;
            try {
                data = draggedData || JSON.parse(e.dataTransfer.getData('text/plain'));
            } catch (err) {
                console.error("Invalid drag data", err);
                return;
            }

            // Lógica según zona
            if (type === 'exclusion') {
                addExclusionChip(data.term);
            } else if (type === 'synonym') {
                // Agregar término y sus sinónimos
                addSynonymChip(element, data.term);
                if (data.synonyms) {
                    data.synonyms.split(',').forEach(s => {
                        if (s.trim()) addSynonymChip(element, s.trim());
                    });
                }
            } else if (type === 'main') {
                // Al soltar en Main Term Zone, reemplazamos el placeholder
                setMainTerm(element, data.term, data.synonyms);
            }

            updateStringPreview();
        });
    }

    // ==========================================
    // MANEJO DE GRUPOS
    // ==========================================
    function createNewGroup(term = '', synonyms = []) {
        if (emptyMsg) emptyMsg.style.display = 'none';

        const groupDiv = document.createElement('div');
        groupDiv.className = "card border border-base-200 shadow-sm mb-2 group-block transition-all hover:shadow-md relative overflow-visible";

        // Template del Main Term Zone (Vacío o Lleno)
        // Usamos un div clickeable/droppable en lugar de input
        let mainTermHTML = '';
        if (term) {
            mainTermHTML = `
                <div class="main-term-chip badge badge-primary badge-lg font-bold text-white w-full justify-between cursor-grab" draggable="true">
                    <span class="main-term-text truncate">${term}</span>
                    <button class="btn btn-ghost btn-xs btn-circle text-white/70 hover:text-white clear-main-term ml-2">✕</button>
                </div>
            `;
        } else {
            mainTermHTML = `
                <div class="main-term-placeholder h-12 border-2 border-dashed border-base-300 rounded-lg flex items-center justify-center text-base-content/40 text-sm bg-base-100 hover:bg-base-200 transition-colors">
                    Drag Main Keyword Here
                </div>
            `;
        }

        groupDiv.innerHTML = `
        <button class="btn btn-sm btn-circle btn-ghost absolute h-6 w-6 top-0.5 right-2 text-base-content/40 hover:text-error delete-group-btn z-10">✕</button>
        <div class="card-body p-2 pl-4">
            <div class="grid grid-cols-1 md:grid-cols-[1fr_auto_2fr] gap-4 items-stretch">
                <div class="flex flex-col">
                    <h6 class="text-xs font-bold text-primary tracking-wide">
                        Main Concept (AND)
                    </h6>
                    <div class="main-term-zone flex-1 flex flex-col justify-center">
                        ${mainTermHTML}
                    </div>
                </div>
                <div class="divider md:divider-horizontal text-xs text-base-content/30 font-bold mx-0">OR</div>
                <div class="flex flex-col">
                    <h6 class="text-xs font-bold text-secondary tracking-wide">
                        Synonyms / Related (OR)
                    </h6>
                    <div class="synonyms-zone rounded-lg border border-dashed border-gray-400 p-3 flex flex-wrap gap-2 content-start transition-colors">
                        <div class="text-xs text-base-content/30 w-full text-center pointer-events-none empty-syn-msg self-center mt-4">
                            Drag synonyms here
                        </div>
                    </div>
                </div>

            </div>
        </div>
    `;

        // Eventos
        groupDiv.querySelector('.delete-group-btn').addEventListener('click', () => {
            groupDiv.remove();
            if (strategyCanvas.querySelectorAll('.group-block').length === 0) {
                if (emptyMsg) emptyMsg.style.display = 'block';
            }
            updateStringPreview();
        });

        // Setup Dropzones
        const mainZone = groupDiv.querySelector('.main-term-zone');
        setupDropZone(mainZone, 'main'); // Zona especial para Main Term

        const synZone = groupDiv.querySelector('.synonyms-zone');
        setupDropZone(synZone, 'synonym');

        // Si ya venía con datos (Carga inicial)
        if (term) {
            setupMainTermEvents(mainZone, synZone);
        }
        synonyms.forEach(syn => addSynonymChip(synZone, syn));

        strategyCanvas.appendChild(groupDiv);
        updateStringPreview();
    }

    function setMainTerm(container, text, synonymsStr) {
        // Reemplazar el placeholder con el chip
        container.innerHTML = `
            <div class="main-term-chip badge badge-primary badge-lg font-bold text-white w-full justify-between cursor-grab" draggable="true">
                <span class="main-term-text truncate">${text}</span>
                <button class="btn btn-ghost btn-xs btn-circle text-white/70 hover:text-white clear-main-term ml-2">✕</button>
            </div>
        `;

        // Agregar automáticamente los sinónimos asociados al grupo de abajo
        const groupCard = container.closest('.card');
        const synZone = groupCard.querySelector('.synonyms-zone');

        if (synonymsStr) {
            synonymsStr.split(',').forEach(s => {
                if (s.trim()) addSynonymChip(synZone, s.trim());
            });
        }

        setupMainTermEvents(container, synZone);
        updateStringPreview();
    }

    function setupMainTermEvents(container, synZone) {
        const clearBtn = container.querySelector('.clear-main-term');
        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Evitar drag
                // Volver a estado placeholder
                container.innerHTML = `
                    <div class="main-term-placeholder h-12 border-2 border-dashed border-base-300 rounded-lg flex items-center justify-center text-base-content/40 text-sm bg-base-100 hover:bg-base-200 transition-colors">
                        Drag Main Keyword Here
                    </div>
                `;
                updateStringPreview();
            });
        }
        // Aquí podrías agregar lógica para que el main term también sea draggeable hacia otro lado si quisieras
    }

    function addSynonymChip(container, text) {
        const msg = container.querySelector('.empty-syn-msg');
        if (msg) msg.style.display = 'none';

        // Evitar duplicados
        const existing = Array.from(container.querySelectorAll('.synonym-val')).map(el => el.textContent);
        if (existing.includes(text)) return;

        const chip = document.createElement('div');
        chip.className = "badge badge-outline gap-2 shadow-sm hover:border-primary transition-colors cursor-default align-middle justify-center flex";
        chip.innerHTML = `
            <span class="synonym-val font-medium">${text}</span>
            <button class="btn btn-ghost btn-xs btn-circle h-4 w-4 min-h-0 text-base-content/40 hover:text-error hover:bg-white hover:border-0 hover:border-white remove-chip">✕</button>
        `;

        chip.querySelector('.remove-chip').addEventListener('click', () => {
            chip.remove();
            if (container.children.length <= 1) if (msg) msg.style.display = 'block';
            updateStringPreview();
        });

        container.appendChild(chip);
        updateStringPreview();
    }

    // ==========================================
    // EXCLUSIONES MANUALES
    // ==========================================
    function addManualExclusion() {
        const text = manualExclInput.value.trim();
        if (text) {
            addExclusionChip(text);
            manualExclInput.value = '';
            updateStringPreview();
        }
    }

    function addExclusionChip(text) {
        const msg = document.querySelector('.empty-excl-msg');
        if (msg) msg.style.display = 'none';

        const existing = Array.from(exclusionsZone.querySelectorAll('.exclusion-val')).map(el => el.textContent);
        if (existing.includes(text)) return;

        const chip = document.createElement('div');
        chip.className = "badge badge-error text-white gap-2 h-auto shadow-sm";
        chip.innerHTML = `
            <span class="font-bold opacity-70">NOT</span>
            <span class="exclusion-val font-bold">${text}</span>
            <button class="btn btn-ghost btn-xs btn-circle h-6 w-6 min-h-0 text-white/70 hover:text-white remove-chip">✕</button>
        `;

        chip.querySelector('.remove-chip').addEventListener('click', () => {
            chip.remove();
            if (exclusionsZone.children.length <= 1) if (msg) msg.style.display = 'block';
            updateStringPreview();
        });

        exclusionsZone.insertBefore(chip, exclusionsZone.firstChild); // Insertar antes del placeholder
    }

    // ==========================================
    // DATA COLLECTION
    // ==========================================
    function collectData() {
        const mainTerms = [];

        document.querySelectorAll('.group-block').forEach(group => {
            // Buscamos el texto dentro del chip, NO un input value
            const termEl = group.querySelector('.main-term-text');
            if (termEl) {
                const termValue = termEl.textContent.trim();
                const synonyms = [];
                group.querySelectorAll('.synonym-val').forEach(span => {
                    synonyms.push(span.textContent.trim());
                });

                mainTerms.push({
                    term: termValue,
                    synonyms: synonyms
                });
            }
        });

        const exclusions = [];
        document.querySelectorAll('.exclusion-val').forEach(span => {
            exclusions.push(span.textContent.trim());
        });

        return { main_terms: mainTerms, exclusions: exclusions };
    }

    function loadFromJSON(data) {
        // Limpiar canvas primero
        strategyCanvas.innerHTML = '';
        // Restaurar Grupos
        if (data.main_terms && data.main_terms.length > 0) {
            data.main_terms.forEach(group => {
                createNewGroup(group.term, group.synonyms);
            });
        } else {
            createNewGroup();
        }
        // Restaurar Exclusiones
        if (data.exclusions && data.exclusions.length > 0) {
            data.exclusions.forEach(exc => addExclusionChip(exc));
        }
    }

    function saveAndSearch() {
        const visualData = collectData();
        if (visualData.main_terms.length === 0) {
            showToast("Please add at least one main term group.", ToastType.WARNING);
            return;
        }

        const loader = document.getElementById('full-screen-loader');
        if (loader) loader.classList.remove('hidden');

        fetch(SAVE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ visual_data: visualData })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.location.href = data.redirect_url;
                } else {
                    showToast("Error: " + data.error, ToastType.ERROR);
                    if (loader) loader.classList.add('hidden');
                }
            })
            .catch(err => {
                console.error(err);
                showToast("Network error.", ToastType.ERROR);
                if (loader) loader.classList.add('hidden');
            });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});