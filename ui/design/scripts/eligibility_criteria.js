document.addEventListener("DOMContentLoaded", () => {
    const mainContainer = document.querySelector('[data-project-id]');
    if (!mainContainer) return;

    const projectId = mainContainer.dataset.projectId;
    const isPastStage = mainContainer.dataset.isPastStage === 'true';
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Modal elements
    const reviewModal = document.getElementById('review_modal');
    const reviewForm = document.getElementById('review-form');
    const modalTitle = document.getElementById('modal-title');
    const modalCriterionId = document.getElementById('modal-criterion-id');
    const modalActionType = document.getElementById('modal-action-type');
    const modalJustification = document.getElementById('modal-justification');

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

        const data = await response.json();
        if (!response.ok || data.success === false) {
            throw new Error(data.error || 'An error occurred');
        }

        return data;
    };

    const updateRowState = (tr, status, justification) => {
        // 1. Update Status Badge
        const statusCell = tr.querySelector('td:nth-child(3)');
        status = status.toUpperCase();
        let badgeClass = 'badge badge-ghost text-xs';
        let badgeText = 'Draft';

        if (status === 'APPROVED') {
            badgeClass = 'badge badge-success text-xs text-white';
            badgeText = 'Approved';
        } else if (status === 'REJECTED') {
            badgeClass = 'badge badge-error text-xs text-white';
            badgeText = 'Rejected';
        }
        statusCell.innerHTML = `<span class="${badgeClass}">${badgeText}</span>`;

        // 2. Update Actions Column (Info Button)
        const actionsContainer = tr.querySelector('td:nth-child(4) .flex');
        let infoBtn = actionsContainer.querySelector('.tooltip:has(button)');

        if (!infoBtn) {
            const firstChild = actionsContainer.firstElementChild;
            if (firstChild && firstChild.classList.contains('tooltip')) {
                infoBtn = firstChild;
            }
        }

        if (justification) {
            if (!infoBtn) {
                infoBtn = document.createElement('div');
                infoBtn.className = 'tooltip';
                infoBtn.innerHTML = `
                    <button class="btn btn-ghost btn-xs">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
                            stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
                            <path stroke-linecap="round" stroke-linejoin="round"
                                d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                        </svg>
                    </button>
                `;
                actionsContainer.prepend(infoBtn);
            }
            infoBtn.setAttribute('data-tip', justification);
        } else {
            if (infoBtn) infoBtn.remove();
        }
    };

    // Handle Review Form Submission
    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const criterionId = modalCriterionId.value;
            const actionType = modalActionType.value; // 'approve' or 'reject'
            const justification = modalJustification.value;

            // Find the row
            const tr = document.querySelector(`tr[data-id="${criterionId}"]`);
            if (!tr) return;

            try {
                let url;
                if (actionType === 'approve') {
                    url = URLS.approve.replace('9999', criterionId);
                } else {
                    url = URLS.reject.replace('9999', criterionId);
                }

                const data = await apiCall(url, 'POST', { justification });
                updateRowState(tr, data.status, justification);
                reviewModal.close();
                reviewForm.reset();

            } catch (error) {
                console.error(`${actionType} failed:`, error);
                showToast(`Error: ${error.message}`, ToastType.ERROR);
            }
        });
    }

    const bindRowEvents = (tr) => {
        const descriptionCell = tr.querySelector('td:nth-child(1) > div');
        const motivationCell = tr.querySelector('td:nth-child(2) > div');
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

        tr.querySelector('.approve-btn')?.addEventListener('click', (e) => {
            const criterionId = tr.dataset.id;
            if (!criterionId) return;

            if (isPastStage) {
                if (!confirm("This stage is already consolidated. Are you sure you want to modify this criterion?")) return;
            }

            modalCriterionId.value = criterionId;
            modalActionType.value = 'approve';
            modalTitle.textContent = 'Approve Criterion';
            reviewForm.reset(); // clear previous
            reviewModal.showModal();
        });

        tr.querySelector('.reject-btn')?.addEventListener('click', (e) => {
            const criterionId = tr.dataset.id;
            if (!criterionId) return;

            if (isPastStage) {
                if (!confirm("This stage is already consolidated. Are you sure you want to modify this criterion?")) return;
            }

            modalCriterionId.value = criterionId;
            modalActionType.value = 'reject';
            modalTitle.textContent = 'Reject Criterion';
            reviewForm.reset();
            reviewModal.showModal();
        });

        tr.querySelector('.delete-btn')?.addEventListener('click', async () => {
            const criterionId = tr.dataset.id;
            if (!criterionId) {
                tr.remove();
                return;
            }

            let message = 'Are you sure you want to delete this criterion?';
            if (isPastStage) {
                message = "This stage is already consolidated. Are you sure you want to DELETE this criterion?";
            }

            if (confirm(message)) {
                try {
                    const url = URLS.delete.replace('9999', criterionId);
                    await apiCall(url, 'POST');
                    tr.remove();
                } catch (error) {
                    console.error('Delete failed:', error);
                    showToast(`Error: ${error.message}`, ToastType.ERROR);
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
                <span class="badge badge-neutral gap-1 text-white">Draft</span>
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
    const addInclusionBtn = document.getElementById("add-inclusion-btn");
    if (addInclusionBtn) {
        addInclusionBtn.addEventListener("click", (e) => {
            e.preventDefault();
            addRow("inclusion-table-body");
        });
    }

    const addExclusionBtn = document.getElementById("add-exclusion-btn");
    if (addExclusionBtn) {
        addExclusionBtn.addEventListener("click", (e) => {
            e.preventDefault();
            addRow("exclusion-table-body");
        });
    }
});
