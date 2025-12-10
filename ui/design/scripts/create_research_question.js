document.addEventListener('DOMContentLoaded', function () {
    console.log('create_research_question.js loaded');
    const questionModal = document.getElementById('question_modal');
    const addQuestionBtn = document.getElementById('add-question-btn');
    const tableBody = document.getElementById('question-table-body');

    console.log('Elements found:', { questionModal, addQuestionBtn, tableBody });

    // Form Elements
    const form = document.getElementById('question-form');
    const fieldsContainer = document.getElementById('fields-container');
    const questionIdInput = document.getElementById('research-question-id');
    const autosaveStatus = document.getElementById('autosave-status');
    const submitContainer = document.getElementById('submit-container');

    // Inputs
    const questionInput = document.getElementById('question');
    const motivationInput = document.getElementById('motivation');
    const frameworkInputs = document.querySelectorAll('.framework-field-input');

    let lastSavedData = '';

    // --- 1. Modal Logic ---

    if (addQuestionBtn) {
        addQuestionBtn.addEventListener('click', () => {
            console.log('Add Question Clicked');
            resetForm();
            questionModal.showModal();
        });
    }

    if (tableBody) {
        tableBody.addEventListener('click', (e) => {
            console.log('Table Body Clicked', e.target);
            const row = e.target.closest('tr.question-row');
            if (row && !e.target.closest('.delete-btn, .view-strategy-btn, a')) {
                // If we have JSON data, use it
                if (row.dataset.questionJson) {
                    try {
                        // In Django templates, we might need to handle single quotes if not strictly JSON
                        // But using |safe and to_json in template usually gives valid JSON
                        // Let's assume the data attribute has the JSON string
                        console.log('Parsing JSON:', row.dataset.questionJson);
                        const questionData = JSON.parse(row.dataset.questionJson);
                        populateForm(questionData);
                        questionModal.showModal();
                    } catch (err) {
                        console.error("Error parsing question JSON", err);
                    }
                } else {
                    // Fallback or if data is missing
                    console.warn("No data-question-json found on row");
                }
            }
        });
    }

    function resetForm() {
        form.reset();
        questionIdInput.value = '';
        autosaveStatus.innerHTML = '';
        lastSavedData = '';

        // Reset framework fields manually if needed (form.reset() should handle it if they are inputs)
        // Reset submit button state
        updateSubmitButton('DRAFT');
    }

    function populateForm(data) {
        resetForm();
        questionIdInput.value = data.id || '';
        questionInput.value = data.question || '';
        motivationInput.value = data.motivation || '';

        // Populate Framework Fields
        if (data.framework_fields) {
            frameworkInputs.forEach(input => {
                const fieldName = input.dataset.field;
                if (data.framework_fields[fieldName]) {
                    input.value = data.framework_fields[fieldName];
                }
            });
        }

        // Update Submit Button based on status
        updateSubmitButton(data.status);

        // Update Form Action
        if (data.id) {
            form.action = submitUrlTemplate.replace('9999', data.id);
        }

        // Set initial saved data state to avoid immediate autosave trigger
        const formData = new FormData(form);
        lastSavedData = new URLSearchParams(formData).toString();
    }

    function updateSubmitButton(status) {
        if (!submitContainer) return;

        if (status === 'READY_TO_SEND' || status === 'SUGGESTED') {
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


    // --- 2. Autosave Logic (Adapted) ---

    function debounce(func, delay) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    function triggerAutosave() {
        if (!fieldsContainer) return;

        const formData = new FormData(form);
        const currentDataString = new URLSearchParams(formData).toString();

        if (currentDataString === lastSavedData) {
            return;
        }

        // Saving State
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
                    // Saved State
                    autosaveStatus.innerHTML = `
                    <div class="flex items-center gap-2 text-base-content/50 transition-all duration-500 ease-in-out" title="All changes saved to cloud">
                        <span class="text-xs font-bold uppercase tracking-wide">Saved</span>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5">
                            <path fill-rule="evenodd" d="M19.916 4.626a.75.75 0 0 1 .208 1.04l-9 13.5a.75.75 0 0 1-1.154.114l-6-6a.75.75 0 0 1 1.06-1.06l5.353 5.353 8.493-12.74a.75.75 0 0 1 1.04-.207Z" clip-rule="evenodd" />
                        </svg>
                    </div>
                `;

                    questionIdInput.value = data.id;
                    lastSavedData = currentDataString;
                    form.action = submitUrlTemplate.replace('9999', data.id);
                    updateSubmitButton(data.status);

                } else {
                    console.error('Autosave failed:', data.error);
                    autosaveStatus.innerHTML = `<span class="text-error text-xs font-bold">Error Saving</span>`;
                }
            })
            .catch(error => {
                console.error('Autosave request failed:', error);
                autosaveStatus.innerHTML = `<span class="text-error text-xs font-bold">Network Error</span>`;
            });
    }

    if (fieldsContainer) {
        const debouncedAutosave = debounce(triggerAutosave, 2000);
        fieldsContainer.addEventListener('input', debouncedAutosave);
    }

    // Initial check if we are on the standalone page (create_research_question.html) 
    // and there is data pre-loaded (QUESTION_DATA global variable)
    if (typeof QUESTION_DATA !== 'undefined' && QUESTION_DATA !== null) {
        populateForm(QUESTION_DATA);
    }
});