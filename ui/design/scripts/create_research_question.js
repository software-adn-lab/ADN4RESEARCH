document.addEventListener('DOMContentLoaded', function () {
    const fieldsContainer = document.getElementById('fields-container');
    if (!fieldsContainer) return;

    const form = document.getElementById('question-form');
    const questionIdInput = document.getElementById('research-question-id');
    const autosaveStatus = document.getElementById('autosave-status');
    let lastSavedData = '';

    function debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    function triggerAutosave() {
        const formData = new FormData(form);
        const currentDataString = new URLSearchParams(formData).toString();
        
        // Si no hay cambios, no hacemos nada (el icono se queda en "Saved" si ya estaba)
        if (currentDataString === lastSavedData) {
            return;
        }

        // --- ESTADO 1: GUARDANDO (Spinner Azul) ---
        autosaveStatus.innerHTML = `
            <div class="flex items-center gap-2 text-primary transition-opacity duration-300">
                <span class="text-xs font-bold uppercase tracking-wide">Saving...</span>
                <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            </div>
        `;

        fetch(autosaveUrl, { 
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                // --- ESTADO 2: GUARDADO (Check Gris - Estilo Word) ---
                // Se queda fijo, indicando que todo está seguro en la nube.
                autosaveStatus.innerHTML = `
                    <div class="flex items-center gap-2 text-base-content/50 transition-all duration-500 ease-in-out" title="All changes saved to cloud">
                        <span class="text-xs font-bold uppercase tracking-wide">Saved</span>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                            <path fill-rule="evenodd" d="M19.916 4.626a.75.75 0 0 1 .208 1.04l-9 13.5a.75.75 0 0 1-1.154.114l-6-6a.75.75 0 0 1 1.06-1.06l5.353 5.353 8.493-12.74a.75.75 0 0 1 1.04-.207Z" clip-rule="evenodd" />
                        </svg>
                    </div>
                `;
                
                // Actualizamos IDs y Datos
                questionIdInput.value = data.id;
                lastSavedData = currentDataString;
                form.action = submitUrlTemplate.replace('9999', data.id);

                // Actualizar botón Submit
                const submitContainer = document.getElementById('submit-container');
                if (submitContainer) {
                    if (data.status === 'READY_TO_SEND') {
                        submitContainer.innerHTML = `
                            <button type="submit" class="btn btn-primary text-white gap-2 px-8 animate-pulse-once">
                                Submit Question
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                                </svg>
                            </button>`;
                    } else {
                        submitContainer.innerHTML = `
                            <div class="tooltip tooltip-left" data-tip="Fill all fields to enable submission">
                                <button class="btn btn-disabled btn-outline">Complete fields to submit</button>
                            </div>`;
                    }
                }

            } else {
                console.error('Autosave failed:', data.error);
                autosaveStatus.innerHTML = `
                    <div class="flex items-center gap-2 text-error" title="Error saving">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                            <path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clip-rule="evenodd" />
                        </svg>
                        <span class="text-xs font-bold uppercase">Not Saved</span>
                    </div>`;
            }
        })
        .catch(error => {
            console.error('Autosave request failed:', error);
            autosaveStatus.innerHTML = `<span class="text-error text-xs font-bold">Network Error</span>`;
        });
    }

    const debouncedAutosave = debounce(triggerAutosave, 2000); 
    fieldsContainer.addEventListener('input', debouncedAutosave);
});