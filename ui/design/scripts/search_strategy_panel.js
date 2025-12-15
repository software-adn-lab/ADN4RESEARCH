document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('strategy_versions_modal');
    const tableBody = document.getElementById('versions-table-body');
    const viewButtons = document.querySelectorAll('.view-versions-btn');

    viewButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const questionId = btn.dataset.id;
            openHistoryModal(questionId);
        });
    });

    function openHistoryModal(questionId) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-base-content/50"><span class="loading loading-spinner"></span> Loading history...</td></tr>';
        modal.showModal();

        const url = versionsApiUrl.replace('0', questionId);

        fetch(url)
            .then(response => response.json())
            .then(data => renderTable(data.versions, questionId))
            .catch(error => {
                console.error('Error:', error);
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-error py-4">Error loading versions.</td></tr>';
            });
    }

    function renderTable(versions, questionId) {
        if (!versions || versions.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-base-content/50">No versions found. Build a strategy first.</td></tr>';
            return;
        }

        tableBody.innerHTML = '';

        versions.forEach(ver => {
            const row = document.createElement('tr');
            row.className = "hover";

            row.innerHTML = `
                <td class="font-bold text-center">${ver.version}</td>
                <td title="${ver.string}">
                    <div class="font-mono text-xs whitespace-normal break-words">${ver.string}</div>
                </td>
                <td class="text-center font-semibold">${ver.total_found}</td>
                <td class="text-center">
                    <span class="badge badge-sm ${getStatusBadgeClass(ver.status)}">${ver.status}</span>
                </td>
                <td class="text-xs text-base-content/70">${ver.date}</td>
                <td class="text-center">
                    <div class="flex justify-center gap-2">
                        <a href="${builderUrlBase}?question_id=${questionId}&version_id=${ver.id}" type="button" 
                                class="btn btn-xs btn-primary text-white btn-circle action-btn" 
                                data-action="reload"
                                title="Reload this version to Builder">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
                            </svg>
                        </a>

                        <button type="button" 
                                class="btn btn-xs btn-success text-white btn-circle action-btn" 
                                data-action="approve"
                                data-strategy-id="${ver.strategy_id}"
                                title="Approve Strategy">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>
                        </button>
                        
                        <button type="button"
                                class="btn btn-xs btn-error btn-outline btn-circle action-btn"
                                data-action="reject"
                                data-strategy-id="${ver.strategy_id}"
                                title="Reject Strategy">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
                        </button>

                        <button type="button" 
                                class="btn btn-ghost btn-xs text-base-content/60 hover:bg-base-300 action-btn delete-btn" 
                                data-action="delete"
                                data-version-id="${ver.id}"
                                title="Delete">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3m9 0H6" /></svg>
                        </button>
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    // 4. Manejo de Acciones (Event Delegation)
    tableBody.addEventListener('click', (e) => {
        const btn = e.target.closest('.action-btn');
        if (!btn) return;

        const action = btn.dataset.action; // 'approve', 'reject', 'delete'
        const strategyId = btn.dataset.strategyId;
        const versionId = btn.dataset.versionId;

        console.log('Action clicked:', action, 'Strategy ID:', strategyId, 'Version ID:', versionId);

        if (action === 'approve') {
            openReviewModal(approveUrlBase.replace('0', strategyId), 'Approve');
        } else if (action === 'reject') {
            openReviewModal(rejectUrlBase.replace('0', strategyId), 'Reject');
        } else if (action === 'delete') {
            performAction(deleteVersionApiUrl.replace('0', versionId), 'Delete');
        }
    });

    function openReviewModal(actionUrl, actionType) {
        console.log('Opening review modal:', actionType, actionUrl);
        const modal = document.getElementById('review_strategy_modal');
        const form = document.getElementById('review-strategy-form');
        const title = document.getElementById('review-modal-title');
        const confirmBtn = document.getElementById('review-confirm-btn');

        if (!modal) {
            console.error('Review modal not found!');
            return;
        }

        form.action = actionUrl;
        title.textContent = `${actionType} Strategy`;

        if (actionType === 'Approve') {
            confirmBtn.className = 'btn btn-success text-white';
            confirmBtn.textContent = 'Confirm Approval';
        } else {
            confirmBtn.className = 'btn btn-error text-white';
            confirmBtn.textContent = 'Confirm Rejection';
        }

        modal.showModal();
    }

    // 5. Llamada AJAX para Delete (Approve/Reject van por form submit)
    function performAction(url, actionName) {
        if (!confirm(`Are you sure you want to ${actionName} this strategy?`)) return;

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url; // Seguir redirección del backend
                } else {
                    // Si el backend no redirige (devuelve JSON), recargar
                    window.location.reload();
                }
            })
            .catch(error => {
                console.error('Action failed:', error);
                alert('Action failed. See console.');
            });
    }

    // Helper CSRF
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

    function getStatusBadgeClass(status) {
        switch (status) {
            case 'APPROVED': return 'badge-success text-white';
            case 'REJECTED': return 'badge-error text-white';
            default: return 'badge-ghost';
        }
    }
});