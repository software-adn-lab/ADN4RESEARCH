document.addEventListener('DOMContentLoaded', function () {
    const fieldsContainer = document.getElementById('fields-container');
    if (!fieldsContainer) return;

    const form = document.getElementById('question-form');
    const questionIdInput = document.getElementById('research-question-id');
    const autosaveStatus = document.getElementById('autosave-status');
    let lastSavedData = '';
    let saveStatusTimeout;

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
        if (currentDataString === lastSavedData) {
            return;
        }
        clearTimeout(saveStatusTimeout);
        autosaveStatus.innerHTML = `
            <div class="flex items-center text-gray-500">
                <svg class="mr-2 size-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Saving...
            </div>
        `;

        fetch(autosaveUrl, { // Uses the global autosaveUrl variable
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                autosaveStatus.innerHTML = `
                    <div class="flex items-center text-green-600">
                        <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 size-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                        </svg>
                        Question Saved Successfully
                    </div>
                `;
                saveStatusTimeout = setTimeout(() => {
                    autosaveStatus.innerHTML = '';
                }, 1500);
                questionIdInput.value = data.id;
                lastSavedData = currentDataString;
                form.action = submitUrlTemplate.replace('9999', data.id);

                const submitContainer = document.getElementById('submit-container');
                if (submitContainer) {
                    if (data.status === 'READY_TO_SEND') {
                        submitContainer.innerHTML = '<button type="submit" class="btn btn-primary mt-4">Submit Question</button>';
                    } else {
                        submitContainer.innerHTML = '<p class="text-gray-500 mt-4">Complete all fields to enable submission</p>';
                    }
                }

            } else {
                console.error('Autosave failed:', data.error);
                autosaveStatus.innerHTML = `<span class="text-red-500">Autosave failed.</span>`;
            }
        })
        .catch(error => console.error('Autosave request failed:', error));
    }

    const debouncedAutosave = debounce(triggerAutosave, 3000);
    fieldsContainer.addEventListener('input', debouncedAutosave);
});