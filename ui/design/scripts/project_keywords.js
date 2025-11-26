document.addEventListener("DOMContentLoaded", () => {
    const mainContainer = document.querySelector('[data-project-id]');
    if (!mainContainer) return;

    const projectId = mainContainer.dataset.projectId;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    const debounce = (func, delay) => {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    };

    const apiCall = async (url, body) => {
        const formData = new FormData();
        if (body) {
            for (const key in body) {
                formData.append(key, body[key]);
            }
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'An error occurred');
        }
        return response.json();
    };

    const bindRowEvents = (tr) => {
        const termCell = tr.querySelector('td:nth-child(1) > div');
        const synonymsCell = tr.querySelector('td:nth-child(2) > div');
        const autosaveStatusEl = tr.querySelector('.autosave-status');
        let lastSavedData = `${termCell.textContent.trim()}|${synonymsCell.textContent.trim()}`;

        const saveChanges = async () => {
            const keywordId = tr.dataset.id;
            const term = termCell.textContent.trim();
            const synonyms = synonymsCell.textContent.trim();
            const currentData = `${term}|${synonyms}`;

            if (currentData === lastSavedData) return;
            if (!term) {
                if (!keywordId) tr.remove(); // Remove unsaved empty row
                return;
            }

            autosaveStatusEl.innerHTML = `<span class="text-base-content/60">Saving...</span>`;

            try {
                let data;
                if (keywordId) { // Update existing keyword
                    const url = KEYWORD_URLS.update.replace('9999', keywordId);
                    data = await apiCall(url, { term, synonyms });
                } else { // Create new keyword
                    const url = KEYWORD_URLS.create;
                    data = await apiCall(url, { term, synonyms });
                    tr.dataset.id = data.keyword_id; // Set the new ID on the row
                }
                lastSavedData = currentData;
                autosaveStatusEl.innerHTML = `<span class="text-success">Saved!</span>`;
            } catch (error) {
                console.error('Save failed:', error);
                autosaveStatusEl.innerHTML = `<span class="text-error">Failed!</span>`;
            } finally {
                setTimeout(() => { autosaveStatusEl.innerHTML = '' }, 2000);
            }
        };

        const debouncedSaveChanges = debounce(saveChanges, 1500);
        [termCell, synonymsCell].forEach(cell => {
            cell.addEventListener('input', debouncedSaveChanges);
            cell.addEventListener('blur', saveChanges); // Save immediately on blur
        });

        tr.querySelector('.delete-keyword-btn')?.addEventListener('click', async () => {
            const keywordId = tr.dataset.id;
            if (!keywordId) { // If row was never saved, just remove it
                tr.remove();
                return;
            }
            if (confirm('Are you sure you want to delete this key term?')) {
                try {
                    const url = KEYWORD_URLS.delete.replace('9999', keywordId);
                    await apiCall(url);
                    tr.remove();
                } catch (error) {
                    console.error('Delete failed:', error);
                }
            }
        });
    };

    const addRow = () => {
        const tableBody = document.getElementById("keyword-table-body");
        const tr = document.createElement("tr");
        tr.className = "hover:bg-base-200 transition-colors";
        tr.innerHTML = `
            <td class="p-2">
                <div contenteditable="true" class="editable-cell focus:outline-none w-full p-1 rounded" data-placeholder="Enter key term"></div>
            </td>
            <td class="p-2">
                <div contenteditable="true" class="editable-cell focus:outline-none w-full p-1 rounded" data-placeholder="Enter synonyms, separated by commas"></div>
            </td>
            <td class="p-2 text-center">
                <div class="flex justify-center gap-2">
                    <button class="btn btn-ghost btn-xs text-base-content/60 hover:bg-base-300 delete-keyword-btn" title="Delete">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3m9 0H6" /></svg>
                    </button>
                </div>
                <div class="autosave-status text-xs h-4 mt-1"></div>
            </td>
        `;
        tableBody.appendChild(tr);
        bindRowEvents(tr);
        tr.querySelector('.editable-cell').focus();
    };

    // Bind events to existing rows loaded from the server
    document.querySelectorAll('#keyword-table-body tr').forEach(bindRowEvents);

    // Event listener for 'Add' button
    document.getElementById("add-keyword-btn").addEventListener("click", (e) => {
        e.preventDefault();
        addRow();
    });
});