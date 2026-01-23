// Make instance globally accessible for inline onclick handlers
window.membersManagerInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    const objectivesManager = new FormsetManager('specific_objectives', 'objectives-container');
    const resultsManager = new FormsetManager('expected_results', 'results-container');
    window.membersManagerInstance = new MembersManager();
    
    // Date validation
    const startDateInput = document.getElementById('start-date-input');
    const endDateInput = document.getElementById('end-date-input');
    const dateError = document.getElementById('date-error');
    
    if (startDateInput && endDateInput && dateError) {
        const validateDates = () => {
            const startDate = new Date(startDateInput.value);
            const endDate = new Date(endDateInput.value);
            
            if (startDateInput.value && endDateInput.value) {
                if (endDate < startDate) {
                    dateError.textContent = 'End date must be greater than or equal to start date.';
                    dateError.classList.remove('hidden');
                    endDateInput.classList.add('input-error');
                    return false;
                } else {
                    dateError.classList.add('hidden');
                    endDateInput.classList.remove('input-error');
                    return true;
                }
            }
            return true;
        };
        
        startDateInput.addEventListener('change', validateDates);
        endDateInput.addEventListener('change', validateDates);
        
        // Prevent form submission if dates are invalid
        const form = startDateInput.closest('form');
        if (form) {
            form.addEventListener('submit', (e) => {
                if (!validateDates()) {
                    e.preventDefault();
                    alert('Please correct the date range before submitting.');
                }
            });
        }
    }
});

class MembersManager {
    constructor() {
        this.members = [];
        this.memberSelect = document.getElementById('member-select');
        this.workloadInput = document.getElementById('workload-input');
        this.addButton = document.getElementById('add-member-btn');
        this.membersList = document.getElementById('members-list');
        this.hiddenInput = document.getElementById('id_members_workload');

        if (!this.memberSelect || !this.workloadInput || !this.addButton || !this.membersList || !this.hiddenInput) {
            console.warn('MembersManager: Required elements not found');
            return;
        }

        this.addButton.addEventListener('click', () => this.addMember());
    }

    addMember() {
        const selectedOption = this.memberSelect.options[this.memberSelect.selectedIndex];
        const userId = selectedOption.value.trim();
        const username = selectedOption.dataset.username || selectedOption.text;
        const fullname = selectedOption.dataset.fullname || selectedOption.text;
        const workload = parseInt(this.workloadInput.value) || 0;

        if (!userId || userId === '' || userId === '--') {
            alert('Please select a member');
            return;
        }

        if (workload < 0 || workload > 168) {
            alert('Workload must be between 0 and 168 hours per week');
            return;
        }

        // Check if member already added
        if (this.members.find(m => m.user_id === parseInt(userId))) {
            alert('Member already added');
            return;
        }

        // Add to members array
        this.members.push({
            user_id: parseInt(userId),
            username: username,
            fullname: fullname,
            workload: workload
        });

        // Update UI
        this.renderMembers();
        this.updateHiddenInput();

        // Reset form
        this.memberSelect.selectedIndex = 0;
        this.workloadInput.value = 8;
    }

    removeMember(userId) {
        this.members = this.members.filter(m => m.user_id !== userId);
        this.renderMembers();
        this.updateHiddenInput();
    }

    renderMembers() {
        if (this.members.length === 0) {
            this.membersList.innerHTML = '<p class="text-sm text-base-content/50 italic">No members added yet</p>';
            return;
        }

        this.membersList.innerHTML = this.members.map(member => `
            <div class="flex items-center justify-between p-3 bg-base-200 rounded-lg">
                <div class="flex-1">
                    <p class="font-semibold text-sm">${member.fullname}</p>
                    <p class="text-xs text-base-content/60">@${member.username}</p>
                </div>
                <div class="flex items-center gap-3">
                    <span class="badge badge-primary">${member.workload}h/week</span>
                    <button type="button" class="btn btn-square btn-ghost btn-xs text-error" 
                            onclick="window.membersManagerInstance.removeMember(${member.user_id})">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                    </button>
                </div>
            </div>
        `).join('');
    }

    updateHiddenInput() {
        const data = this.members.map(m => ({
            user_id: m.user_id,
            workload: m.workload
        }));
        this.hiddenInput.value = JSON.stringify(data);
    }
}

class FormsetManager {
    constructor(prefix, containerId) {
        this.prefix = prefix;
        this.container = document.getElementById(containerId);
        this.totalFormsInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
        this.addButton = document.getElementById(`add-${prefix}-btn`);

        if (!this.container || !this.totalFormsInput || !this.addButton) {
            console.warn(`FormsetManager: Elements not found for prefix ${prefix}`);
            return;
        }

        this.addButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.addForm();
        });
        this.container.querySelectorAll('.delete-row-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.deleteForm(e));
        });
    }

    addForm() {
        const currentCount = parseInt(this.totalFormsInput.value);
        const templateElement = document.getElementById(`${this.prefix}-empty-form`);
        if (!templateElement) {
            console.error(`Empty form template not found for ${this.prefix}`);
            return;
        }

        const newFormHtml = templateElement.innerHTML.replace(new RegExp('__prefix__', 'g'), currentCount);
        const newRow = document.createElement('div');
        newRow.className = 'form-row flex items-center gap-2 animate-fade-in-down';
        newRow.innerHTML = newFormHtml;
        this.container.appendChild(newRow);
        this.totalFormsInput.value = currentCount + 1;

        const deleteBtn = newRow.querySelector('.delete-row-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => this.deleteForm(e));
        }
    }

    deleteForm(e) {
        const row = e.target.closest('.form-row');
        row.remove();
        this.reindexForms();
    }

    reindexForms() {
        const forms = this.container.querySelectorAll('.form-row');

        forms.forEach((row, index) => {
            row.querySelectorAll('input, textarea, select').forEach(input => {
                if (input.name) {
                    input.name = input.name.replace(new RegExp(`${this.prefix}-\\d+-`), `${this.prefix}-${index}-`);
                }
                if (input.id) {
                    input.id = input.id.replace(new RegExp(`${this.prefix}-\\d+-`), `${this.prefix}-${index}-`);
                }
            });
        });

        this.totalFormsInput.value = forms.length;
    }
}
