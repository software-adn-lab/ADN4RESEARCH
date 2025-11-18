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

    const apiCall = async (url, method, body) => {
        const formData = new FormData();
        if (body) {
            for (const key in body) {
                formData.append(key, body[key]);
            }
        }

        const response = await fetch(url, {
            method: method,
            headers: { 'X-CSRFToken': csrfToken },
            body: method === 'POST' ? formData : null,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'An error occurred');
        }
        return response.json();
    };

    const updateStatusBadge = (statusEl, status) => {
        status = status.toUpperCase();
        statusEl.textContent = status.charAt(0) + status.slice(1).toLowerCase();
        let badgeClass = 'badge badge-ghost text-xs';
        if (status === 'APPROVED') {
            badgeClass = 'badge badge-success text-xs';
        } else if (status === 'REJECTED') {
            badgeClass = 'badge badge-error text-xs';
        }
        statusEl.className = badgeClass;
    };

    const bindRowEvents = (tr) => {
        const descriptionCell = tr.querySelector('td:nth-child(1) > div');
        const motivationCell = tr.querySelector('td:nth-child(2) > div');
        const statusEl = tr.querySelector('.badge');
        const autosaveStatusEl = tr.querySelector('.autosave-status');
        const criterionType = tr.closest('tbody').id === 'inclusion-table-body' ? 'INCLUSION' : 'EXCLUSION';
        let lastSavedData = `${descriptionCell.textContent.trim()}|${motivationCell.textContent.trim()}`;

        const saveChanges = async () => {
            const criterionId = tr.dataset.id;
            const description = descriptionCell.textContent.trim();
            const motivation = motivationCell.textContent.trim();
            const currentData = `${description}|${motivation}`;

            if (currentData === lastSavedData) return;
            if (!description) {
                if (!criterionId) tr.remove();
                return;
            }

            autosaveStatusEl.innerHTML = `<span class="text-base-content/60">Saving...</span>`;

            try {
                let data;
                if (criterionId) {
                    const url = URLS.update.replace('9999', criterionId);
                    data = await apiCall(url, 'POST', { description, motivation });
                } else {
                    const url = URLS.create;
                    data = await apiCall(url, 'POST', { description, motivation, type: criterionType });
                    tr.dataset.id = data.criterion_id;
                }
                lastSavedData = currentData;
                autosaveStatusEl.innerHTML = `<span class="text-success">Saved!</span>`;
            } catch (error) {
                console.error('Save failed:', error);
                autosaveStatusEl.innerHTML = `<span class="text-error">Failed!</span>`;
            } finally {
                setTimeout(() => {
                    autosaveStatusEl.innerHTML = '';
                }, 2000);
            }
        };

        const debouncedSaveChanges = debounce(saveChanges, 2000);

        [descriptionCell, motivationCell].forEach(cell => {
            cell.addEventListener('input', debouncedSaveChanges);
            cell.addEventListener('blur', saveChanges);
        });

        tr.querySelector('.approve-btn')?.addEventListener('click', async () => {
            const criterionId = tr.dataset.id;
            if (!criterionId) return;
            try {
                const url = URLS.approve.replace('9999', criterionId);
                const data = await apiCall(url, 'POST');
                updateStatusBadge(statusEl, data.status);
            } catch (error) {
                console.error('Approve failed:', error);
            }
        });

        tr.querySelector('.reject-btn')?.addEventListener('click', async () => {
            const criterionId = tr.dataset.id;
            if (!criterionId) return;
            try {
                const url = URLS.reject.replace('9999', criterionId);
                const data = await apiCall(url, 'POST');
                updateStatusBadge(statusEl, data.status);
            } catch (error) {
                console.error('Reject failed:', error);
            }
        });

        tr.querySelector('.delete-btn')?.addEventListener('click', async () => {
            const criterionId = tr.dataset.id;
            if (!criterionId) {
                tr.remove();
                return;
            }
            if (confirm('Are you sure you want to delete this criterion?')) {
                try {
                    const url = URLS.delete.replace('9999', criterionId);
                    await apiCall(url, 'POST');
                    tr.remove();
                } catch (error) {
                    console.error('Delete failed:', error);
                }
            }
        });
    };

    const addRow = (tableBodyId) => {
        const tableBody = document.getElementById(tableBodyId);
        const tr = document.createElement("tr");
        tr.className = "hover:bg-base-200 transition-colors";
        tr.innerHTML = `
            <td class="p-2">
                <div contenteditable="true" class="editable-cell focus:outline-none w-full p-1 rounded" data-placeholder="Enter description"></div>
            </td>
            <td class="p-2">
                <div contenteditable="true" class="editable-cell focus:outline-none w-full p-1 rounded" data-placeholder="Enter motivation"></div>
            </td>
            <td class="p-2 text-center">
                <span class="badge badge-ghost text-xs">Draft</span>
            </td>
            <td class="p-2 text-center">
                <div class="flex justify-center gap-2">
                    <button class="btn btn-ghost btn-xs text-success hover:bg-success/10 approve-btn" title="Approve">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                    </button>
                    <button class="btn btn-ghost btn-xs text-error hover:bg-error/10 reject-btn" title="Reject">
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                    <button class="btn btn-ghost btn-xs text-base-content/60 hover:bg-base-300 delete-btn" title="Delete">
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
    document.querySelectorAll('#inclusion-table-body tr, #exclusion-table-body tr').forEach(bindRowEvents);

    // Event listeners for 'Add' buttons
    document.getElementById("add-inclusion-btn").addEventListener("click", (e) => {
        e.preventDefault();
        addRow("inclusion-table-body");
    });
    document.getElementById("add-exclusion-btn").addEventListener("click", (e) => {
        e.preventDefault();
        addRow("exclusion-table-body");
    });
});