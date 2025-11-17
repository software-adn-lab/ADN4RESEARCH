// theme_discovery.js - AI-Driven Theme Discovery functionality
document.addEventListener('DOMContentLoaded', function () {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // === Normalize Codes ===
    const normalizeBtn = document.getElementById('normalize-codes-btn');
    if (normalizeBtn) {
        normalizeBtn.addEventListener('click', async function () {
            this.disabled = true;
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Processing...';

            try {
                const response = await fetch(URLS.normalizeyCodes, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to normalize codes'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to normalize codes');
            } finally {
                this.disabled = false;
                this.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>Normalize Codes with AI';
            }
        });
    }

    // === Accept/Reject Normalization Proposal ===
    document.querySelectorAll('.accept-proposal-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const row = this.closest('tr');
            const proposalId = row.dataset.proposalId;
            await handleProposalAction(proposalId, 'accept', row);
        });
    });

    document.querySelectorAll('.reject-proposal-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const row = this.closest('tr');
            const proposalId = row.dataset.proposalId;
            await handleProposalAction(proposalId, 'reject', row);
        });
    });

    async function handleProposalAction(proposalId, action, row) {
        try {
            const url = URLS.acceptProposal.replace('9999', proposalId);
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ action: action })
            });

            const data = await response.json();
            if (data.success) {
                const actionsCell = row.querySelector('td:last-child');
                if (action === 'accept') {
                    actionsCell.innerHTML = '<span class="badge badge-success text-xs">Accepted</span>';
                } else {
                    actionsCell.innerHTML = '<span class="badge badge-error text-xs">Rejected</span>';
                }
            } else {
                alert('Error: ' + (data.error || 'Failed to process proposal'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to process proposal');
        }
    }

    // === Accept All Proposals ===
    const acceptAllBtn = document.getElementById('accept-all-btn');
    if (acceptAllBtn) {
        acceptAllBtn.addEventListener('click', async function () {
            this.disabled = true;
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Processing...';

            try {
                const response = await fetch(URLS.acceptAllProposals, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to accept all proposals'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to accept all proposals');
            }
        });
    }

    // === Proceed to Theme Generation ===
    const proceedBtn = document.getElementById('proceed-to-themes-btn');
    if (proceedBtn) {
        proceedBtn.addEventListener('click', function () {
            window.location.href = window.location.pathname + '?step=2';
        });
    }

    // === Generate Themes ===
    const generateThemesBtn = document.getElementById('generate-themes-btn');
    if (generateThemesBtn) {
        generateThemesBtn.addEventListener('click', async function () {
            this.disabled = true;
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Processing...';

            try {
                const response = await fetch(URLS.generateThemes, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to generate themes'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to generate themes');
            }
        });
    }

    // === Accept/Reject Theme Proposal ===
    document.querySelectorAll('.accept-theme-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const proposalId = this.dataset.proposalId;
            await handleThemeAction(proposalId, 'accept', this);
        });
    });

    document.querySelectorAll('.reject-theme-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            const proposalId = this.dataset.proposalId;
            await handleThemeAction(proposalId, 'reject', this);
        });
    });

    async function handleThemeAction(proposalId, action, btn) {
        try {
            const url = URLS.acceptTheme.replace('9999', proposalId);
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ action: action })
            });

            const data = await response.json();
            if (data.success) {
                const card = btn.closest('.card-body').querySelector('.flex.flex-col');
                if (action === 'accept') {
                    card.innerHTML = '<span class="badge badge-success">Accepted</span>';
                } else {
                    card.innerHTML = '<span class="badge badge-error">Rejected</span>';
                }
            } else {
                alert('Error: ' + (data.error || 'Failed to process theme'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to process theme');
        }
    }

    // === Accept All Themes ===
    const acceptAllThemesBtn = document.getElementById('accept-all-themes-btn');
    if (acceptAllThemesBtn) {
        acceptAllThemesBtn.addEventListener('click', async function () {
            this.disabled = true;
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Processing...';

            try {
                const response = await fetch(URLS.acceptAllThemes, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to accept all themes'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to accept all themes');
            }
        });
    }

    // === Finalize Themes ===
    const finalizeBtn = document.getElementById('finalize-themes-btn');
    if (finalizeBtn) {
        finalizeBtn.addEventListener('click', async function () {
            this.disabled = true;
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Creating...';

            try {
                const response = await fetch(URLS.finalizeThemes, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                const data = await response.json();
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to finalize themes'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to finalize themes');
            }
        });
    }

    // === Editable Theme Names (Reflexivity Tracking) ===
    document.querySelectorAll('[contenteditable="true"]').forEach(element => {
        let originalValue = element.textContent.trim();
        let saveTimeout;

        element.addEventListener('blur', function () {
            clearTimeout(saveTimeout);
            const newValue = this.textContent.trim();
            
            if (newValue !== originalValue && newValue !== '') {
                saveThemeName(this.dataset.proposalId, newValue, originalValue);
                originalValue = newValue;
            } else if (newValue === '') {
                this.textContent = originalValue;
            }
        });

        element.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur();
            } else if (e.key === 'Escape') {
                this.textContent = originalValue;
                this.blur();
            }
        });

        element.addEventListener('input', function () {
            clearTimeout(saveTimeout);
            const newValue = this.textContent.trim();
            
            if (newValue !== originalValue && newValue !== '') {
                saveTimeout = setTimeout(() => {
                    saveThemeName(this.dataset.proposalId, newValue, originalValue);
                    originalValue = newValue;
                }, 1000);
            }
        });
    });

    async function saveThemeName(proposalId, newName, originalName) {
        try {
            const url = URLS.acceptTheme.replace('9999', proposalId);
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ 
                    action: 'modify',
                    new_name: newName,
                    original_name: originalName
                })
            });

            const data = await response.json();
            if (data.success) {
                // Show subtle feedback
                const element = document.getElementById(`theme-name-${proposalId}`);
                element.classList.add('bg-success/20');
                setTimeout(() => {
                    element.classList.remove('bg-success/20');
                }, 300);
            } else {
                alert('Error: ' + (data.error || 'Failed to save theme name'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to save theme name');
        }
    }
});
