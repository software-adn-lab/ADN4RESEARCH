document.addEventListener('DOMContentLoaded', () => {

    const objectivesManager = new FormsetManager('specific_objectives', 'objectives-container');
    const resultsManager = new FormsetManager('expected_results', 'results-container');

});

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
        newRow.className = 'form-row mb-2 flex items-start gap-2 animate-fade-in-down';
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
