document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('my_modal_3');
    if (!modal) return; // Salir si el modal no está en la página

    const modalStrategyName = document.getElementById('modal-strategy-name');
    const modalSearchString = document.getElementById('modal-search-string');
    const projectContainer = document.querySelector('[data-project-id]');
    
    if (!projectContainer || !modalStrategyName || !modalSearchString) {
        console.error('Faltan elementos requeridos para el modal de estrategia de búsqueda.');
        return;
    }

    const projectId = projectContainer.dataset.projectId;

    // Usar delegación de eventos en el body para asegurar que los botones funcionen
    // incluso si se añaden dinámicamente.
    document.body.addEventListener('click', (event) => {
        const button = event.target.closest('.view-strategy-btn');
        if (button) {
            // Prevenir cualquier otro evento de click (como la navegación de la fila)
            event.stopPropagation(); 

            const questionId = button.dataset.questionId;
            if (!questionId) {
                console.error('El ID de la pregunta no se encuentra en el botón.');
                return;
            }

            const url = `/design/get-strategy/project/${projectId}/question/${questionId}/`;

            // Restablecer el contenido del modal y mostrarlo
            modalStrategyName.textContent = 'Search Strategy';
            modalSearchString.textContent = 'Loading...';
            modal.showModal();

            fetch(url)
                .then(response => {
                    if (!response.ok) {
                        // Intenta obtener un mensaje de error del JSON si es posible
                        return response.json().then(err => { throw new Error(err.error || 'La respuesta de la red no fue correcta') });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        modalStrategyName.textContent = data.strategy_name;
                        modalSearchString.textContent = data.final_search_string || 'Aún no se ha generado una cadena de búsqueda.';
                    } else {
                        modalSearchString.textContent = `Error: ${data.error}`;
                    }
                })
                .catch(error => {
                    console.error('Error al obtener la estrategia de búsqueda:', error);
                    modalSearchString.textContent = `No se pudo cargar la estrategia de búsqueda: ${error.message}`;
                });
        }
    });
});