document.addEventListener('DOMContentLoaded', () => {
    const objectivesManager = new FormsetManager('specific_objectives', 'objectives-container', '.delete-row-btn');
    const resultsManager = new FormsetManager('expected_results', 'results-container', '.delete-row-btn');
    const membersManager = new FormsetManager('members', 'members-container', '.delete-member-btn');

    // Antes de enviar, elimina filas de miembros vacías y reindexa
    const form = document.querySelector('form');
    if (form && membersManager) {
        form.addEventListener('submit', () => {
            membersManager.removeEmptyRows();
        });
    }

});

class FormsetManager {
    constructor(prefix, containerId, deleteButtonSelector = '.delete-row-btn') {
        this.prefix = prefix;
        this.container = document.getElementById(containerId);
        this.totalFormsInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
        this.addButton = document.getElementById(`add-${prefix}-btn`);
        this.deleteButtonSelector = deleteButtonSelector;
        this.memberOptions = null; // cache of all member options (value + text)

        if (!this.container || !this.totalFormsInput || !this.addButton) {
            return;
        }

        this.addButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.addForm();
        });
        this.container.querySelectorAll(this.deleteButtonSelector).forEach(btn => {
            btn.addEventListener('click', (e) => this.deleteForm(e));
        });

        if (this.prefix === 'members') {
            // Cache all available options from the first select
            const firstSelect = this.container.querySelector('select');
            if (firstSelect) {
                this.memberOptions = Array.from(firstSelect.options).map(opt => ({
                    value: opt.value,
                    text: opt.text,
                }));
            }
            this.setupMemberFiltering();
        }
    }

    addForm() {
        const currentCount = parseInt(this.totalFormsInput.value);
        const templateElement = document.getElementById(`${this.prefix}-empty-form`);
        if (!templateElement) {
            return;
        }

        // Capture current selections to filter new selects (for members)
        let selectedValues = new Set();
        if (this.prefix === 'members') {
            selectedValues = new Set(
                Array.from(this.container.querySelectorAll('select'))
                    .map(sel => sel.value)
                    .filter(v => v)
            );
        }

        const newFormHtml = templateElement.innerHTML.replace(new RegExp('__prefix__', 'g'), currentCount);
        
        const temp = document.createElement('div');
        temp.innerHTML = newFormHtml;
        const newRow = temp.firstElementChild;

        if (this.prefix === 'members') {
            const select = newRow.querySelector('select');
            if (select) {
                this.populateSelectOptions(select, '', selectedValues);
            }
        }

        this.container.appendChild(newRow);
        this.totalFormsInput.value = currentCount + 1;

        const deleteBtn = newRow.querySelector(this.deleteButtonSelector);
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => this.deleteForm(e));
        }

        if (this.prefix === 'members') {
            this.setupMemberFilteringForRow(newRow);
            this.updateMemberOptions();
        }
    }

    deleteForm(e) {
        const row = e.target.closest('.form-row, .member-row');
        row.remove();
        this.reindexForms();

        if (this.prefix === 'members') {
            this.updateMemberOptions();
        }
    }

    reindexForms() {
        const forms = this.container.querySelectorAll('.form-row, .member-row');

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

    removeEmptyRows() {
        if (this.prefix !== 'members') return;
        const rows = Array.from(this.container.querySelectorAll('.member-row'));
        rows.forEach(row => {
            const select = row.querySelector('select');
            const workload = row.querySelector('input[type="number"]');
            const isEmpty = (!select || !select.value) && (!workload || !workload.value);
            if (isEmpty) {
                row.remove();
            }
        });
        this.reindexForms();
    }

    setupMemberFiltering() {
        this.container.querySelectorAll('select').forEach(select => {
            select.addEventListener('change', () => this.updateMemberOptions());
        });
        this.updateMemberOptions();
    }

    setupMemberFilteringForRow(row) {
        const select = row.querySelector('select');
        if (!select) return;
        select.addEventListener('change', () => this.updateMemberOptions());
        // Ensure options reflect current selections
        this.populateSelectOptions(select, select.value);
    }

    updateMemberOptions() {
        if (!this.memberOptions || !this.memberOptions.length) return;

        const selects = Array.from(this.container.querySelectorAll('select'));
        const selectedValues = new Set(
            selects
                .map(sel => sel.value)
                .filter(v => v) // ignore empty selections
        );

        selects.forEach(select => {
            const currentValue = select.value;
            this.populateSelectOptions(select, currentValue, selectedValues);
        });
    }

    populateSelectOptions(select, currentValue, selectedValues = new Set()) {
        // Preserve empty option if exists
        select.innerHTML = '';

        this.memberOptions.forEach(({ value, text }) => {
            // Allow empty option
            if (!value) {
                const opt = document.createElement('option');
                opt.value = value;
                opt.textContent = text;
                select.appendChild(opt);
                return;
            }

            // If another select has this value selected, skip unless it's the current select's own value
            if (value !== currentValue && selectedValues.has(value)) {
                return;
            }

            const opt = document.createElement('option');
            opt.value = value;
            opt.textContent = text;
            select.appendChild(opt);
        });

        // Restore current value if still available
        select.value = currentValue && Array.from(select.options).some(o => o.value === currentValue)
            ? currentValue
            : '';
    }
}
