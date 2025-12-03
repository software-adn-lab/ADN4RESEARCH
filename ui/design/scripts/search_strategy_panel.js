document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('strategy_versions_modal');
    const tableBody = document.getElementById('versions-table-body');
    const viewButtons = document.querySelectorAll('.view-versions-btn');

    // 1. Escuchar clicks en los botones de "Ver Historial" (Ojo)
    viewButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const questionId = btn.dataset.id;
            openHistoryModal(questionId);
        });
    });

    // 2. Función para abrir modal y cargar datos
    function openHistoryModal(questionId) {
        // Limpiar tabla y mostrar loading
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-base-content/50"><span class="loading loading-spinner"></span> Loading history...</td></tr>';
        
        modal.showModal();

        // Construir URL dinámica (reemplazando el placeholder 0)
        // versionsApiUrl viene definida en el HTML
        const url = versionsApiUrl.replace('0', questionId);

        fetch(url)
            .then(response => response.json())
            .then(data => {
                renderTable(data.versions, questionId);
            })
            .catch(error => {
                console.error('Error:', error);
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-error py-4">Error loading versions.</td></tr>';
            });
    }

    // 3. Renderizar Tabla
    function renderTable(versions, questionId) {
        if (!versions || versions.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-base-content/50">No versions found. Build a strategy first.</td></tr>';
            return;
        }

        tableBody.innerHTML = ''; // Limpiar

        versions.forEach(ver => {
            const row = document.createElement('tr');
            row.className = "hover";
            
            // Lógica para truncar el string largo
            const shortString = ver.string.length > 50 ? ver.string.substring(0, 50) + '...' : ver.string;

            row.innerHTML = `
                <td class="font-bold text-center">${ver.version}</td>
                <td title="${ver.string}">
                    <div class="font-mono text-xs break-all">${shortString}</div>
                </td>
                <td class="text-center font-semibold">${ver.total_found}</td>
                <td class="text-xs text-base-content/70">${ver.date}</td>
                <td class="text-center">
                    <a href="${builderUrlBase}?question_id=${questionId}&version_id=${ver.id}" 
                       class="btn btn-xs btn-outline btn-primary gap-1"
                       title="Load this version into the Builder">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        Load
                    </a>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
});