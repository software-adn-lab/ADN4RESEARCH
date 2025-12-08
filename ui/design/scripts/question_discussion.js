document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('review_modal');
    const modalTitle = document.getElementById('modal-title');
    const modalQuestionId = document.getElementById('modal-question-id');
    const modalVerdict = document.getElementById('modal-verdict');
    const modalJustification = document.getElementById('modal-justification');
    const reviewForm = document.getElementById('review-form');

    // 1. Manejo de botones de Apertura del Modal
    document.body.addEventListener('click', (e) => {
        const btn = e.target.closest('.review-btn');
        if (!btn) return;

        const mainContainer = document.querySelector('[data-project-id]');
        if (mainContainer) {
            const isPastStage = mainContainer.dataset.isPastStage === 'true';
            if (isPastStage) {
                if (!confirm("This stage is already consolidated. Are you sure you want to review this question?")) return;
            }
        }

        const questionId = btn.dataset.id;
        const action = btn.dataset.action; // 'APPROVED' o 'REJECTED'

        // Configurar el Modal
        modalQuestionId.value = questionId;
        modalVerdict.value = action;
        modalJustification.value = ''; // Limpiar justificación anterior

        // Estilar el título según la acción
        if (action === 'APPROVED') {
            modalTitle.textContent = 'Approve Question';
            modalTitle.className = 'font-bold text-lg text-success';
        } else {
            modalTitle.textContent = 'Reject Question';
            modalTitle.className = 'font-bold text-lg text-error';
        }

        modal.showModal();
    });

    // 2. Manejo del Envío del Formulario (AJAX)
    reviewForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const formData = new FormData(reviewForm);
        const submitBtn = document.getElementById('confirm-review-btn');
        const originalText = submitBtn.textContent;

        // Feedback visual de carga
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading loading-spinner"></span> Processing...';

        fetch(reviewUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    modal.close();
                    // Recargar la página para actualizar la tabla y estados
                    window.location.reload();
                } else {
                    alert('Error: ' + data.message);
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An unexpected error occurred.');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            });
    });
});