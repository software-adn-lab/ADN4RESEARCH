/**
 * TagManager Component
 * Responsabilidad: Actualizar tags obligatorios, calcular coverage
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
        // Escuchar cuando se crea una quote
        window.addEventListener('quote:created', (e) => {
            this.updateMandatoryTagsUI(e.detail.quote.tags);
        });
    }

    updateMandatoryTagsUI(quoteTags) {
        quoteTags.forEach(tag => {
            const badge = document.querySelector(`[data-tag-id="${tag.id}"]`);
            if (badge && !badge.classList.contains('badge-success')) {
                badge.classList.remove('badge-ghost');
                badge.classList.add('badge-success', 'text-white');
                badge.style.opacity = '1';
                badge.title = '✅ Tag cubierto';

                if (!badge.querySelector('svg')) {
                    const checkmark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    checkmark.setAttribute('class', 'inline-block w-3 h-3 stroke-current');
                    checkmark.setAttribute('fill', 'none');
                    checkmark.setAttribute('viewBox', '0 0 24 24');
                    checkmark.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>';
                    badge.insertBefore(checkmark, badge.firstChild);
                    badge.insertBefore(document.createTextNode(' '), badge.firstChild.nextSibling);
                }
            }
        });

        this.updateCoveragePercentage();
        this.updateMissingTagsAlert();
    }

    updateCoveragePercentage() {
        console.group('🔍 Debug: updateCoveragePercentage');

        // 1. Identificar qué estamos seleccionando como "Total"
        // ⚠️ OJO: Esto selecciona CUALQUIER elemento con data-tag-id en toda la página
        const allMandatoryBadges = document.querySelectorAll('#mandatory-tags-container [data-tag-id]');
        
        // 2. Identificar cuáles considera "Cubiertos"
        const coveredBadges = document.querySelectorAll('[data-tag-id].badge-success');
        
        const totalMandatory = allMandatoryBadges.length;
        const coveredCount = coveredBadges.length;
        
        console.log(`📊 Conteo: ${coveredCount} cubiertos de ${totalMandatory} totales.`);
        
        // Loguear los IDs para ver si hay duplicados o elementos incorrectos
        const totalIds = Array.from(allMandatoryBadges).map(el => el.dataset.tagId);
        console.log('📋 IDs Totales encontrados:', totalIds);
        
        const coveredIds = Array.from(coveredBadges).map(el => el.dataset.tagId);
        console.log('✅ IDs Cubiertos detectados:', coveredIds);

        if (totalMandatory === 0) {
            console.warn('⚠️ No se encontraron etiquetas obligatorias. Saliendo.');
            console.groupEnd();
            return;
        }
        
        const percentage = Math.round((coveredCount / totalMandatory) * 100);
        console.log(`🧮 Cálculo: (${coveredCount} / ${totalMandatory}) * 100 = ${percentage}%`);

        const progressContainer = document.querySelector('#coverage-progress-container');
        
        if (!progressContainer) {
            console.error('❌ No se encontró el contenedor #coverage-progress-container en el DOM');
        } else {
            const progressBar = progressContainer.querySelector('.progress');
            const badge = progressContainer.querySelector('.badge');
            
            console.log('UI Updates:', { 
                foundBar: !!progressBar, 
                foundBadge: !!badge,
                newPercentage: percentage 
            });

            if (progressBar) {
                progressBar.value = percentage;
                // ... lógica de clases ...
                progressBar.classList.remove('progress-success', 'progress-warning', 'progress-error');
                if (percentage === 100) progressBar.classList.add('progress-success');
                else if (percentage >= 50) progressBar.classList.add('progress-warning');
                else progressBar.classList.add('progress-error');
            }

            if (badge) {
                badge.textContent = `${percentage}%`;
                // ... lógica de clases ...
                badge.classList.remove('badge-warning', 'badge-success', 'badge-error');
                if (percentage === 100) badge.classList.add('badge-success');
                else if (percentage >= 50) badge.classList.add('badge-warning');
                else badge.classList.add('badge-error');
            }
        }
        
        console.groupEnd();
    }
}

window.TagManager = TagManager;