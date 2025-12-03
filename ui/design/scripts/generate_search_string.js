document.addEventListener('DOMContentLoaded', () => {
    // 1. Obtener referencias al Modal y sus elementos
    const modal = document.getElementById('my_modal_3');
    if (!modal) return; 

    const modalStrategyName = document.getElementById('modal-strategy-name');
    const modalSearchString = document.getElementById('modal-search-string');
    
    // Ya no necesitamos 'projectContainer' ni 'projectId' porque la URL viene lista en el botón.

    // 2. Event Delegation para detectar clics en los botones dinámicos
    document.body.addEventListener('click', (event) => {
        // Buscamos si el clic fue dentro de un botón con la clase .view-strategy-btn
        const button = event.target.closest('.view-strategy-btn');
        
        if (button) {
            event.stopPropagation(); 
            event.preventDefault(); // Buena práctica para evitar saltos raros

            // 3. Extraer la URL generada por Django desde el atributo data-url
            const url = button.dataset.url;
            
            if (!url) {
                console.error('Error: El botón no tiene el atributo data-url definido.');
                return;
            }

            console.log("Solicitando estrategia a:", url); // Debugging

            // 4. Resetear UI y mostrar Modal (Estado de Carga)
            modalStrategyName.textContent = 'Search Strategy';
            modalSearchString.textContent = 'Generating search string...';
            modalSearchString.classList.add('animate-pulse'); // Opcional: efecto visual
            modal.showModal();

            // 5. Petición al Servidor
            fetch(url)
                .then(response => {
                    // Validamos si la respuesta es exitosa (Status 200-299)
                    if (!response.ok) {
                        // Si falla (ej. 500 o 404), leemos el texto para saber qué pasó (probablemente HTML de error)
                        return response.text().then(text => { 
                            throw new Error(`Server Error (${response.status}): ${text.substring(0, 100)}...`);
                        });
                    }
                    // Si todo bien, parseamos el JSON
                    return response.json();
                })
                .then(data => {
                    modalSearchString.classList.remove('animate-pulse');
                    
                    if (data.status === 'success') {
                        // Caso Exitoso
                        modalStrategyName.textContent = data.strategy_name || 'Search Strategy';
                        modalSearchString.textContent = data.final_search_string || 'No search string generated yet.';
                    } else {
                        // El servidor respondió 200 pero con un mensaje de error lógico
                        modalSearchString.innerHTML = `<span class="text-error">Error: ${data.error}</span>`;
                    }
                })
                .catch(error => {
                    // Manejo de errores de red o excepciones
                    console.error('Error AJAX:', error);
                    modalSearchString.classList.remove('animate-pulse');
                    modalSearchString.innerHTML = `<span class="text-error">Failed to load strategy.<br><br>Technical details: ${error.message}</span>`;
                });
        }
    });
});