// Update stage date constraints when phase dates change
document.addEventListener('DOMContentLoaded', function() {
    const phaseStartInput = document.getElementById('design_phase_start');
    const phaseEndInput = document.getElementById('design_phase_end');
    const stageInputs = document.querySelectorAll('.stage-date-input');
    
    function updateStageConstraints() {
        const phaseStart = phaseStartInput.value;
        const phaseEnd = phaseEndInput.value;
        
        // Enable stage inputs only when both phase dates are set
        if (phaseStart && phaseEnd) {
            stageInputs.forEach(input => {
                input.disabled = false;
                input.setAttribute('min', phaseStart);
                input.setAttribute('max', phaseEnd);
            });
        } else {
            // Disable if phase dates not complete
            stageInputs.forEach(input => {
                input.disabled = true;
            });
        }
    }
    
    // Listen to phase date changes
    phaseStartInput.addEventListener('change', updateStageConstraints);
    phaseEndInput.addEventListener('change', updateStageConstraints);
    
    // Also validate phase end is after phase start
    phaseEndInput.addEventListener('change', function() {
        const start = new Date(phaseStartInput.value);
        const end = new Date(phaseEndInput.value);
        
        if (start && end && start >= end) {
            alert('Design Phase end date must be after start date');
            phaseEndInput.value = '';
        }
    });
});