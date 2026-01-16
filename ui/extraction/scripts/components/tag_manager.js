/**
 * TagManager Component
 * Responsibility: Update UI state of tags (Mandatory/Optional), calculate coverage, update progress bar.
 * Style: Adapted for MacOS/Atlas.ti split-view
 */

class TagManager {
    constructor(config) {
        this.config = config;
        console.log('🏷️ TagManager initialized');
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Listen for new quotes to update tag status immediately
        window.addEventListener('quote:created', (e) => {
            this.updateTagsUI(e.detail.quote.tags);
        });
    }

    /**
     * Updates the visual state of specific tags in the sidebar
     * @param {Array} quoteTags - Array of tag objects from the created quote
     */
    updateTagsUI(quoteTags) {
        const container = document.getElementById('mandatory-tags-container');
        if (!container) return;

        quoteTags.forEach(tag => {
            // Find the specific tag chip
            const tagEl = container.querySelector(`[data-tag-id="${tag.id}"]`);
            
            if (tagEl) {
                // Scenario 1: It was a MISSING MANDATORY tag (Red dashed)
                if (tagEl.classList.contains('border-dashed')) {
                    // Update Classes: Red Dashed -> Green Solid
                    tagEl.className = 'inline-flex items-center px-2 py-1 rounded text-[11px] font-medium bg-green-50 text-green-700 border border-green-200 cursor-help transition-all hover:bg-green-100';
                    tagEl.title = 'Mandatory Tag: Covered';
                    
                    // Update Icon: Replace Red Dot with Green Checkmark
                    tagEl.innerHTML = `
                        <svg class="w-3 h-3 mr-1 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                        </svg>
                        ${tag.name}
                    `;
                }
                
                // Scenario 2: It was an UNUSED OPTIONAL tag (Gray)
                else if (tagEl.classList.contains('bg-gray-50')) {
                    // Update Classes: Gray -> Blue
                    tagEl.className = 'inline-flex items-center px-2 py-1 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200';
                    // No icon change needed for optional tags based on your template
                }
            }
        });

        // Recalculate global coverage
        this.updateCoverageLogic();
    }

    updateCoverageLogic() {
        // 1. Selectors based on the new HTML structure
        const container = document.getElementById('mandatory-tags-container');
        if (!container) return;

        // Count Total Mandatory Tags (Green Covered + Red Missing)
        // We identify them by the specific classes used in the HTML template
        const coveredBadges = container.querySelectorAll('.bg-green-50.border-green-200'); // Mandatory Covered
        const missingBadges = container.querySelectorAll('.border-dashed.text-red-600');  // Mandatory Missing
        
        const coveredCount = coveredBadges.length;
        const missingCount = missingBadges.length;
        const totalMandatory = coveredCount + missingCount;

        if (totalMandatory === 0) return; // No mandatory tags configured

        // 2. Calculate Percentage
        const percentage = Math.round((coveredCount / totalMandatory) * 100);
        
        // 3. Update UI Elements
        this.updateProgressBar(percentage);
        this.updateMissingAlert(missingCount);
    }

    updateProgressBar(percentage) {
        const progressContainer = document.getElementById('tag_list_container');
        if (!progressContainer) return;

        // 1. Update Percentage Text
        // Finds the percentage number span
        const percentText = progressContainer.querySelector('.font-mono.font-bold');
        if (percentText) {
            percentText.textContent = `${percentage}%`;
            
            // Color transition
            percentText.classList.remove('text-green-600', 'text-amber-600', 'text-red-600');
            if (percentage === 100) percentText.classList.add('text-green-600');
            else percentText.classList.add('text-amber-600');
        }

        // 2. Update Progress Bar Fill
        // Finds the inner div responsible for the width
        const progressBarFill = progressContainer.querySelector('.w-full.bg-gray-100 > div');
        if (progressBarFill) {
            progressBarFill.style.width = `${percentage}%`;
            
            // Color transition logic matching HTML template
            progressBarFill.classList.remove('bg-green-500', 'bg-amber-400', 'bg-red-400');
            
            if (percentage === 100) {
                progressBarFill.classList.add('bg-green-500');
            } else if (percentage >= 50) {
                progressBarFill.classList.add('bg-amber-400');
            } else {
                progressBarFill.classList.add('bg-red-400');
            }
        }
    }

    updateMissingAlert(missingCount) {
        const alertContainer = document.querySelector('#tag_list_container .text-amber-600.font-medium');
        
        if (missingCount === 0) {
            // Hide the alert if it exists
            if (alertContainer) {
                alertContainer.style.display = 'none';
            }
        } else {
            // If the element exists, update text; if not, we assume it's there from server render
            // or we could recreate it. For now, assuming it exists or we update text.
            if (alertContainer) {
                alertContainer.style.display = 'flex';
                const span = alertContainer.querySelector('span');
                if (span) span.textContent = `Missing ${missingCount} required tags`;
            }
        }
    }
}

window.TagManager = TagManager;