/**
 * Global Alerts System using DaisyUI Toasts
 */

const ToastType = {
    INFO: 'alert-info',
    SUCCESS: 'alert-success',
    WARNING: 'alert-warning',
    ERROR: 'alert-error'
};

function showToast(message, type = ToastType.INFO, duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) {
        console.error('Toast container not found!');
        return;
    }

    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${type} shadow-lg mb-2 animate-fade-in-up`;

    // Icon based on type
    let iconPath = '';
    if (type === ToastType.SUCCESS) {
        iconPath = 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z';
    } else if (type === ToastType.ERROR) {
        iconPath = 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z';
    } else if (type === ToastType.WARNING) {
        iconPath = 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z';
    } else {
        iconPath = 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
    }

    alertDiv.innerHTML = `
        <div>
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${iconPath}" />
            </svg>
            <span>${message}</span>
        </div>
    `;

    container.appendChild(alertDiv);

    // Auto-dismiss
    if (duration > 0) {
        setTimeout(() => {
            alertDiv.classList.add('opacity-0', 'transition-opacity', 'duration-500');
            setTimeout(() => {
                alertDiv.remove();
            }, 500);
        }, duration);
    }
}
