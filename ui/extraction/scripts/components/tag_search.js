/**
 * TagSearch - Filtrado de tags en modal
 */
class TagSearch {
    constructor() {
        this.searchInput = document.getElementById('tag-search-input');
        this.tagsContainer = document.getElementById('tags-list-container');
        this.noTagsMessage = document.getElementById('no-tags-message');
        this.clearBtn = document.getElementById('clear-search-btn');
        this.counter = document.getElementById('tags-counter');
        
        if (this.searchInput) this.init();
    }

    init() {
        this.searchInput.addEventListener('input', (e) => this.filterTags(e.target.value));
        this.clearBtn.addEventListener('click', () => this.clearSearch());
        this.tagsContainer.addEventListener('change', () => this.updateCounter());
        
        
    }

    filterTags(searchTerm) {
        searchTerm = searchTerm.toLowerCase().trim();
        const tagItems = this.tagsContainer.querySelectorAll('.tag-item');
        let visibleCount = 0;

        tagItems.forEach(item => {
            const matches = item.dataset.tagName.includes(searchTerm);
            item.style.display = matches ? 'flex' : 'none';
            if (matches) visibleCount++;
        });

        this.tagsContainer.classList.toggle('hidden', visibleCount === 0 && searchTerm !== '');
        this.noTagsMessage.classList.toggle('hidden', visibleCount > 0 || searchTerm === '');
        this.clearBtn.classList.toggle('hidden', !searchTerm);
    }

    clearSearch() {
        this.searchInput.value = '';
        this.filterTags('');
        this.searchInput.focus();
    }

    updateCounter() {
        const count = this.tagsContainer.querySelectorAll('.tag-checkbox:checked').length;
        this.counter.textContent = count === 0 ? '0 seleccionadas' : 
                                   count === 1 ? '1 seleccionada' : 
                                   `${count} seleccionadas`;
    }
}

// Auto-inicializar
document.addEventListener('DOMContentLoaded', () => new TagSearch());