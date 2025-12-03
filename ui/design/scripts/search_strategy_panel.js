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
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-base-content/50"><span class="loading loading-spinner"></span> Loading history...</td></tr>';
        modal.showModal();

        const url = versionsApiUrl.replace('0', questionId);

        fetch(url)
            .then(response => response.json())
            .then(data => renderTable(data.versions, questionId))
            .catch(error => {
                console.error('Error:', error);
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-error py-4">Error loading versions.</td></tr>';
            });
    }
    function renderTable(versions, questionId) {
        if (!versions || versions.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-base-content/50">No versions found. Build a strategy first.</td></tr>';
            return;
        }

        tableBody.innerHTML = '';

        versions.forEach(ver => {
            const row = document.createElement('tr');
            row.className = "hover";
            
            const shortString = ver.string.length > 50 ? ver.string.substring(0, 50) + '...' : ver.string;
            row.innerHTML = `
                <td class="font-bold text-center">${ver.version}</td>
                <td title="${ver.string}">
                    <div class="font-mono text-xs break-all">${shortString}</div>
                </td>
                <td class="text-center font-semibold">${ver.total_found}</td>
                <td class="text-xs text-base-content/70">${ver.date}</td>
                <td class="text-center">
                    <div class="flex justify-center gap-2">
                        <a href="${builderUrlBase}?question_id=${questionId}&version_id=${ver.id}" 
                           class="btn btn-xs btn-outline btn-primary"
                           title="Load this version to Builder">
                           Load
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

        const action = btn.dataset.action; // 'approve' o 'reject'
        const strategyId = btn.dataset.strategyId;
        
        if (action === 'approve') {
            performAction(approveUrlBase.replace('0', strategyId), 'Approve');
        } else if (action === 'reject') {
            performAction(rejectUrlBase.replace('0', strategyId), 'Reject');
        }
    });

    // 5. Llamada AJAX para Aprobar/Rechazar
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
});