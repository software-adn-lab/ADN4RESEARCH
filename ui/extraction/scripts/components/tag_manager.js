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

/*
    updateMissingTagsAlert() {
        const allMandatoryBadges = document.querySelectorAll('[data-tag-id]');
        const missingTags = [];

        allMandatoryBadges.forEach(badge => {
            if (!badge.classList.contains('badge-success')) {
                missingTags.push({ 
                    id: badge.dataset.tagId, 
                    name: badge.textContent.trim() 
                });
            }
        });

        const alertContainer = document.querySelector('#mandatory_tags');
        if (!alertContainer) return;

        const existingAlert = alertContainer.querySelector('.alert');
        if (existingAlert) existingAlert.remove();

        if (missingTags.length === 0) {
            const successAlert = document.createElement('div');
            successAlert.className = 'alert alert-success mt-3 py-2 text-xs';
            successAlert.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Todos los tags obligatorios han sido cubiertos</span>
            `;
            alertContainer.appendChild(successAlert);
        } else {
            const tagsHtml = missingTags.map(tag => 
                `<span class="badge badge-xs badge-ghost">${tag.name}</span>`
            ).join(' ');

            const warningAlert = document.createElement('div');
            warningAlert.className = 'alert alert-warning mt-3 py-2 text-xs';
            warningAlert.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div class="flex-1">
                    <span class="font-semibold">Faltan ${missingTags.length} tag(s):</span>
                    <div class="flex flex-wrap gap-1 mt-1">${tagsHtml}</div>
                </div>
            `;
            alertContainer.appendChild(warningAlert);
        }
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
    }*/
}

window.TagManager = TagManager;