// theme_discovery.js - AI-Driven Theme Discovery functionality
document.addEventListener('DOMContentLoaded', function () {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    console.log("Holaaaa")

    // === Select All Codes ===
    const selectAllCheckbox = document.getElementById('select-all-codes');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            const checkboxes = document.querySelectorAll('.code-checkbox');
            checkboxes.forEach(cb => cb.checked = this.checked);
        });
    }

    // === Manual Normalization ===
    const manualNormalizeBtn = document.getElementById('manual-normalize-btn');
    const manualModal = document.getElementById('manual-normalization-modal');
    
    if (manualNormalizeBtn) {
        manualNormalizeBtn.addEventListener('click', function () {
            const selectedCheckboxes = document.querySelectorAll('.code-checkbox:checked');
            
            if (selectedCheckboxes.length === 0) {
                alert('Please select at least one code to normalize');
                return;
            }

            // Update the selected codes display
            const selectedCodesList = document.getElementById('selected-codes-list');
            selectedCodesList.innerHTML = '';
            
            selectedCheckboxes.forEach(cb => {
                const badge = document.createElement('span');
                badge.className = 'badge badge-primary';
                badge.textContent = cb.dataset.code;
                selectedCodesList.appendChild(badge);
            });

            manualModal.showModal();
        });
    }

    // === Manual Normalization Form Submit ===
    const manualForm = document.getElementById('manual-normalization-form');
    if (manualForm) {
        manualForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            
            const selectedCheckboxes = document.querySelectorAll('.code-checkbox:checked');
            const originalCodes = Array.from(selectedCheckboxes).map(cb => cb.dataset.code);
            
            const normalizedCode = document.getElementById('manual-normalized-code').value.trim();
            const rationale = document.getElementById('manual-rationale').value.trim();

            if (!normalizedCode || originalCodes.length === 0 || !rationale) {
                alert('Please fill all required fields');
                return;
            }

            try {
                const response = await fetch(URLS.createManualNormalization, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        normalized_code: normalizedCode,
                        original_codes: originalCodes,
                        rationale: rationale
                    })
                });

                const data = await response.json();
                if (data.success) {
                    manualModal.close();
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to create normalization'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to create normalization');
            }
        });
    }

    // === Normalize Codes ===
    const normalizeBtn = document.getElementById('normalize-codes-btn');
    if (normalizeBtn) {
        normalizeBtn.addEventListener('click', async function () {
            console.log("Normalize codes button clicked")
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
            console.log('[DEBUG] Accept All button clicked');
            this.disabled = true;
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Processing...';

            try {
                console.log('[DEBUG] Sending request to:', URLS.acceptAllProposals);
                const response = await fetch(URLS.acceptAllProposals, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });

                console.log('[DEBUG] Response status:', response.status);
                const data = await response.json();
                console.log('[DEBUG] Response data:', data);
                
                if (data.success) {
                    console.log('[DEBUG] Success! Reloading page...');
                    location.reload();
                } else {
                    console.error('[ERROR] Failed:', data.error);
                    alert('Error: ' + (data.error || 'Failed to accept all proposals'));
                    this.disabled = false;
                    this.innerHTML = 'Accept All & Create Normalized Codes';
                }
            } catch (error) {
                console.error('[ERROR] Exception:', error);
                alert('Failed to accept all proposals: ' + error.message);
                this.disabled = false;
                this.innerHTML = 'Accept All & Create Normalized Codes';
            }
        });
    }

    // === Proceed to Theme Generation ===
    const proceedBtn = document.getElementById('proceed-to-themes-btn');
    if (proceedBtn) {
        proceedBtn.addEventListener('click', async function () {
            // First, accept all proposals to create normalized codes
            this.disabled = true;
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Creating normalized codes...';

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
                    // Now proceed to step 2
                    window.location.href = window.location.pathname + '?step=2';
                } else {
                    alert('Error: ' + (data.error || 'Failed to create normalized codes'));
                    this.disabled = false;
                    this.innerHTML = 'Proceed to Theme Generation';
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to proceed. Please try accepting proposals first.');
                this.disabled = false;
                this.innerHTML = 'Proceed to Theme Generation';
            }
        });
    }

    // === Select All Normalized Codes (Step 2) ===
    const selectAllNormalizedCheckbox = document.getElementById('select-all-normalized-codes');
    if (selectAllNormalizedCheckbox) {
        selectAllNormalizedCheckbox.addEventListener('change', function () {
            const checkboxes = document.querySelectorAll('.normalized-code-checkbox');
            checkboxes.forEach(cb => cb.checked = this.checked);
        });
    }

    // === Manual Theme Creation ===
    const manualThemeBtn = document.getElementById('manual-theme-btn');
    const manualThemeModal = document.getElementById('manual-theme-modal');
    
    if (manualThemeBtn) {
        manualThemeBtn.addEventListener('click', function () {
            const selectedCheckboxes = document.querySelectorAll('.normalized-code-checkbox:checked');
            
            if (selectedCheckboxes.length === 0) {
                alert('Please select at least one normalized code for the theme');
                return;
            }

            // Update the selected codes display
            const selectedThemeCodesList = document.getElementById('selected-theme-codes-list');
            selectedThemeCodesList.innerHTML = '';
            
            // Get RQ focus from first selected code (they should all be related)
            const firstRQ = selectedCheckboxes[0].dataset.rq;
            document.getElementById('manual-theme-rq').value = firstRQ;
            
            selectedCheckboxes.forEach(cb => {
                const badge = document.createElement('span');
                badge.className = 'badge badge-primary';
                badge.textContent = cb.dataset.code;
                selectedThemeCodesList.appendChild(badge);
            });

            manualThemeModal.showModal();
        });
    }

    // === Manual Theme Form Submit ===
    const manualThemeForm = document.getElementById('manual-theme-form');
    if (manualThemeForm) {
        manualThemeForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            
            const selectedCheckboxes = document.querySelectorAll('.normalized-code-checkbox:checked');
            const codeIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.dataset.codeId));
            
            const themeName = document.getElementById('manual-theme-name').value.trim();
            const themeDescription = document.getElementById('manual-theme-description').value.trim();
            const researchQuestionFocus = document.getElementById('manual-theme-rq').value.trim();
            const rationale = document.getElementById('manual-theme-rationale').value.trim();

            if (!themeName || !themeDescription || !researchQuestionFocus || codeIds.length === 0 || !rationale) {
                alert('Please fill all required fields');
                return;
            }

            try {
                const response = await fetch(URLS.createManualTheme, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        theme_name: themeName,
                        theme_description: themeDescription,
                        research_question_focus: researchQuestionFocus,
                        code_ids: codeIds,
                        rationale: rationale
                    })
                });

                const data = await response.json();
                if (data.success) {
                    manualThemeModal.close();
                    location.reload();
                } else {
                    alert('Error: ' + (data.error || 'Failed to create theme'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to create theme');
            }
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
            this.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Creating themes...';

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
                    // Redirect to themes created page
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else {
                        alert(`Successfully created ${data.created_count} themes!`);
                        location.reload();
                    }
                } else {
                    alert('Error: ' + (data.error || 'Failed to finalize themes'));
                    this.disabled = false;
                    this.innerHTML = 'Finalize Themes';
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to finalize themes');
                this.disabled = false;
                this.innerHTML = 'Finalize Themes';
            }
        });
    }

    // === Editable RQ Focus for Normalized Codes ===
    document.querySelectorAll('.rq-focus-input').forEach(input => {
        let saveTimeout;

        input.addEventListener('input', function () {
            clearTimeout(saveTimeout);
            const codeId = this.dataset.codeId;
            const newValue = this.value.trim();

            // Auto-save after 1 second of no typing
            saveTimeout = setTimeout(async () => {
                if (newValue) {
                    await saveRQFocus(codeId, newValue);
                }
            }, 1000);
        });

        input.addEventListener('blur', async function () {
            clearTimeout(saveTimeout);
            const codeId = this.dataset.codeId;
            const newValue = this.value.trim();
            
            if (newValue) {
                await saveRQFocus(codeId, newValue);
            }
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur();
            }
        });
    });

    async function saveRQFocus(codeId, rqFocus) {
        try {
            const response = await fetch(URLS.updateRQFocus.replace('9999', codeId), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ rq_focus: rqFocus })
            });

            const data = await response.json();
            if (!data.success) {
                console.error('Failed to save RQ Focus:', data.error);
            }
        } catch (error) {
            console.error('Error saving RQ Focus:', error);
        }
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
