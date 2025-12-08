document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('my_modal_3');
    if (!modal) return;

    const modalStrategyName = document.getElementById('modal-strategy-name');
    const modalSearchString = document.getElementById('modal-search-string');
    const testStrategyBtn = document.getElementById('test-strategy-btn');

    // Helper para obtener el CSRF Token (Estándar en Django)
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

    document.body.addEventListener('click', (event) => {
        const button = event.target.closest('.view-strategy-btn');

        if (button) {
            event.stopPropagation();
            event.preventDefault();

            const url = button.dataset.url;
            const questionId = button.dataset.id;

            if (!url) {
                console.error('Error: El botón no tiene el atributo data-url definido.');
                return;
            }
            modalStrategyName.textContent = 'Search Strategy';
            modalSearchString.textContent = 'Generating search string...';
            modalSearchString.classList.add('animate-pulse');
            if (testStrategyBtn) testStrategyBtn.classList.add('hidden');
            modal.showModal();

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
                .then(response => {
                    if (!response.ok) {
                        return response.text().then(text => {
                            try {
                                const jsonErr = JSON.parse(text);
                                throw new Error(jsonErr.error || `Server Error (${response.status})`);
                            } catch (e) {
                                throw new Error(`Server Error (${response.status})`);
                            }
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    modalSearchString.classList.remove('animate-pulse');

                    if (data.status === 'success') {
                        modalStrategyName.textContent = data.strategy_name || 'Search Strategy';
                        modalSearchString.textContent = data.final_search_string || 'No search string generated yet.';

                        // Show Test Button if configured
                        if (testStrategyBtn && typeof builderUrlBase !== 'undefined') {
                            testStrategyBtn.href = `${builderUrlBase}?question_id=${questionId}`;
                            testStrategyBtn.classList.remove('hidden');
                        }
                    } else {
                        modalSearchString.innerHTML = `<span class="text-error">Error: ${data.error}</span>`;
                    }
                })
                .catch(error => {
                    console.error('Error AJAX:', error);
                    modalSearchString.classList.remove('animate-pulse');
                    modalSearchString.innerHTML = `<span class="text-error text-sm">Failed to generate strategy.<br>${error.message}</span>`;
                });
        }
    });
});