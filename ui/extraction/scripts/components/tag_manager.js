// ui/extraction/static/scripts/components/tag_manager.js

/**
 * TagManager Component
 * Maneja el filtrado y selección de tags
 */

class TagManager {
    constructor(options) {
        this.container = document.querySelector(options.containerSelector);
        this.searchInput = document.querySelector(options.searchInputSelector);
        
        if (!this.container) {
            throw new Error('Tags container not found');
        }
    }
    
    init() {
        console.log('🏷️ Initializing Tag Manager...');
        
        if (this.searchInput) {
            this.searchInput.addEventListener('keyup', () => this.filterTags());
        }
        
        // Exponer función globalmente para compatibilidad con templates
        window.filterTags = () => this.filterTags();
        
        console.log('✅ Tag Manager ready');
    }
    
    filterTags() {
        const filter = this.searchInput ? this.searchInput.value.toLowerCase() : '';
        const items = this.container.getElementsByClassName('tag-item');
        let visibleCount = 0;

        for (let i = 0; i < items.length; i++) {
            const tagName = items[i].getAttribute('data-name');
            if (tagName && tagName.indexOf(filter) > -1) {
                items[i].style.display = "";
                visibleCount++;
            } else {
                items[i].style.display = "none";
            }
        }
        
        const noTagsMsg = document.getElementById('no-tags-msg');
        if (noTagsMsg) {
            noTagsMsg.classList.toggle('hidden', visibleCount > 0);
        }
        
        return visibleCount;
    }
    
    getSelectedTags() {
        return Array.from(
            this.container.querySelectorAll('input[name="tags"]:checked')
        ).map(cb => cb.value);
    }
    
    resetSelection() {
        this.container.querySelectorAll('input[name="tags"]').forEach(cb => {
            cb.checked = false;
        });
        
        if (this.searchInput) {
            this.searchInput.value = '';
        }
        
        this.filterTags();
    }
}

window.TagManager = TagManager;