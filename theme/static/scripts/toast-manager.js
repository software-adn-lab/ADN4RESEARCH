/**
 * Toast Manager - Auto-dismissing toast notifications
 * Shows floating toast messages that auto-close after 3 seconds
 */

(function() {
    'use strict';

    // Add CSS animations first
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fade-in {
            from {
                opacity: 0;
                transform: translateY(-1rem);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fade-out {
            from {
                opacity: 1;
                transform: translateY(0);
            }
            to {
                opacity: 0;
                transform: translateY(-1rem);
            }
        }

        .animate-fade-in {
            animation: fade-in 0.3s ease-out;
        }

        .animate-fade-out {
            animation: fade-out 0.3s ease-out;
        }

        #toast-container {
            pointer-events: none;
        }

        #toast-container > * {
            pointer-events: auto;
        }
    `;
    document.head.appendChild(style);

    class ToastManager {
        constructor() {
            this.duration = 3000; // 3 seconds
        }

        getContainer() {
            return document.getElementById('toast-container');
        }

        show(message, type = 'info') {
            const container = this.getContainer();
            if (!container) {
                console.error('Toast container not found');
                return;
            }

            const toast = document.createElement('div');
            toast.className = `alert shadow-lg ${this.getAlertClass(type)} animate-fade-in`;
            
            toast.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
                    ${this.getIcon(type)}
                </svg>
                <span>${this.escapeHtml(message)}</span>
                <button class="btn btn-sm btn-circle btn-ghost" onclick="this.parentElement.remove()">✕</button>
            `;

            container.appendChild(toast);

            setTimeout(() => {
                this.remove(toast);
            }, this.duration);
        }

        remove(toast) {
            if (!toast || !toast.parentElement) return;
            
            toast.classList.add('animate-fade-out');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        getAlertClass(type) {
            const classes = {
                'success': 'alert-success',
                'error': 'alert-error',
                'warning': 'alert-warning',
                'info': 'alert-info'
            };
            return classes[type] || 'alert-info';
        }

        getIcon(type) {
            const icons = {
                'success': '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />',
                'error': '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />',
                'warning': '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />',
                'info': '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />'
            };
            return icons[type] || icons['info'];
        }
    }

    // Initialize global toast manager
    window.toastManager = new ToastManager();

    // Auto-show Django messages on page load
    function showDjangoMessages() {
        // Try both IDs (one for base.html, one for design templates)
        const messagesData = document.getElementById('django-messages-data') || 
                           document.getElementById('django-messages-data-design');
        
        if (!messagesData) {
            console.log('No django-messages-data found');
            return;
        }

        try {
            const messagesText = messagesData.textContent.trim();
            if (!messagesText) {
                console.log('Messages data is empty');
                return;
            }

            const messages = JSON.parse(messagesText);
            console.log('Parsed messages:', messages);

            if (Array.isArray(messages) && messages.length > 0) {
                messages.forEach(msg => {
                    if (msg.message && msg.type) {
                        window.toastManager.show(msg.message, msg.type);
                    }
                });
            } else {
                console.log('No messages to display (array is empty)');
            }
        } catch (e) {
            console.error('Error parsing Django messages:', e);
        }
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showDjangoMessages);
    } else {
        showDjangoMessages();
    }

})();
