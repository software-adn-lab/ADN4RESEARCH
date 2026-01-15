// Metadata screening decision and navigation
// Handles paper selection, decision modals, and criteria management

let currentAssignmentId = null;
let currentDecision = null;
let currentPaperId = null;
let inclusionCriteria = [];
let exclusionCriteria = [];

function initScreeningViewer(criteriaData) {
    inclusionCriteria = criteriaData.inclusion || [];
    exclusionCriteria = criteriaData.exclusion || [];
}

function openDecisionModal(assignmentId, decision) {
    if (!decision) {
        const btn = document.querySelector(`#review-form-${assignmentId} button.btn-outline`);
        if (btn && btn.classList.contains('btn-disabled')) {
            return;
        }
    }
    currentAssignmentId = assignmentId;
    // if decision is null (edit notes), use the current stored decision
    const detail = document.querySelector(`#paper-${currentPaperId}`) || document.querySelector(`[data-assignment-id="${assignmentId}"]`);
    const existingDecision = detail ? detail.dataset.decision : 'PENDING';
    currentDecision = decision || existingDecision; // can be null when editing notes only but we prefer existing
    
    const notesInput = document.getElementById('notes-' + assignmentId);
    const criterionInput = document.getElementById('criterion-' + assignmentId);
    const modalNotes = document.getElementById('modal-notes-input');
    const select = document.getElementById('modal-criterion-select');
    const title = document.getElementById('modal-title');
    const label = document.getElementById('criterion-label');
    
    modalNotes.value = notesInput.value || '';
    select.innerHTML = '<option value="">Select criterion...</option>';
    
    let criteria = [];
    if (currentDecision === 'INCLUDED') {
        criteria = inclusionCriteria;
        title.textContent = 'Include paper';
        label.textContent = 'Select inclusion criterion';
    } else if (currentDecision === 'EXCLUDED') {
        criteria = exclusionCriteria;
        title.textContent = 'Exclude paper';
        label.textContent = 'Select exclusion criterion';
    } else {
        // editing notes with pending decision should not happen (button disabled), fallback
        criteria = inclusionCriteria.concat(exclusionCriteria);
        title.textContent = 'Edit notes';
        label.textContent = 'Criterion';
    }
    
    const currentCriterion = criterionInput.value || '';
    criteria.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.label;
        if (c.id === currentCriterion) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });
    
    document.getElementById('decision-modal').showModal();
}

function closeDecisionModal() {
    document.getElementById('decision-modal').close();
    currentAssignmentId = null;
    currentDecision = null;
}

function saveDecisionAndNotes() {
    if (!currentAssignmentId) return;
    const form = document.getElementById('review-form-' + currentAssignmentId);
    const notesInput = document.getElementById('notes-' + currentAssignmentId);
    const criterionInput = document.getElementById('criterion-' + currentAssignmentId);
    const criterionLabelInput = document.getElementById('criterion-label-' + currentAssignmentId);
    const modalNotes = document.getElementById('modal-notes-input');
    const select = document.getElementById('modal-criterion-select');
    
    notesInput.value = modalNotes.value;
    criterionInput.value = select.value;
    
    // Get label from selected option
    const selectedOption = select.options[select.selectedIndex];
    criterionLabelInput.value = selectedOption ? selectedOption.text : '';
    
    const formData = new FormData(form);
    // Send the current decision (from button click or existing from data-decision)
    if (currentDecision && currentDecision !== 'PENDING') {
        formData.set('decision', currentDecision);
    }
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeDecisionModal();
            
            // Save scroll position before reload
            const listContainer = document.querySelector('.col-span-4.overflow-y-auto');
            if (listContainer) {
                sessionStorage.setItem('paperListScrollPos', listContainer.scrollTop);
            }
            
            // Stay on the same paper after reload by encoding param
            const paperParam = currentPaperId ? `?paper=${encodeURIComponent(currentPaperId)}` : '';
            window.location = window.location.pathname + paperParam;
        } else {
            console.error('Error:', data.error);
            alert('Failed to save: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to save decision');
    });
}

function showPaperDetail(paperId) {
    // Hide all paper details
    document.querySelectorAll('.paper-detail-content').forEach(el => {
        el.classList.add('hidden');
    });
    
    // Show selected paper
    const paperDetail = document.getElementById('paper-' + paperId);
    if (paperDetail) {
        paperDetail.classList.remove('hidden');
    }
    currentPaperId = paperId;
    
    // Update active state in list
    document.querySelectorAll('.paper-item').forEach(el => {
        el.classList.remove('bg-white', 'border-primary', 'border-l-4');
    });
    
    const paperItem = document.querySelector(`.paper-item[data-paper-id="${paperId}"]`);
    if (paperItem) {
        paperItem.classList.add('bg-white', 'border-primary', 'border-l-4');
        // Scroll within the list container only, not the whole page
        const listContainer = paperItem.closest('.col-span-4');
        if (listContainer) {
            const listScroll = listContainer.querySelector('.overflow-y-auto');
            if (listScroll) {
                const itemTop = paperItem.offsetTop;
                const itemHeight = paperItem.offsetHeight;
                const scrollTop = listScroll.scrollTop;
                const scrollHeight = listScroll.clientHeight;
                
                if (itemTop < scrollTop) {
                    listScroll.scrollTop = itemTop;
                } else if (itemTop + itemHeight > scrollTop + scrollHeight) {
                    listScroll.scrollTop = itemTop + itemHeight - scrollHeight;
                }
            }
        }
    }
}

// Select first paper on load
document.addEventListener('DOMContentLoaded', function() {
    const params = new URLSearchParams(window.location.search);
    const paperFromUrl = params.get('paper');
    let target = null;
    if (paperFromUrl) {
        target = document.querySelector(`.paper-item[data-paper-id="${paperFromUrl}"]`);
    }
    if (!target) {
        target = document.querySelector('.paper-item');
    }
    if (target) {
        const paperId = target.dataset.paperId;
        showPaperDetail(paperId);
        // Scroll into view for usability
        target.scrollIntoView({ block: 'nearest' });
    }
    
    // Restore scroll position if saved
    const savedScrollPos = sessionStorage.getItem('paperListScrollPos');
    if (savedScrollPos !== null) {
        const listContainer = document.querySelector('.col-span-4.overflow-y-auto');
        if (listContainer) {
            listContainer.scrollTop = parseInt(savedScrollPos);
            sessionStorage.removeItem('paperListScrollPos');
        }
    }
});
