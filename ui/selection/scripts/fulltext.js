// Full-text screening PDF viewer
// Handles PDF loading, zoom, navigation, and paper actions

pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

let currentAssignmentId = null;
let currentDecision = null;
let currentPaperId = null;

// Store PDF instances and zoom levels
const pdfInstances = {};
const zoomLevels = {};

// URLs injected from template
let retryUrl, uploadUrl;

function initFulltextViewer(urls) {
    retryUrl = urls.retry;
    uploadUrl = urls.upload;
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function getCSRFToken() {
    return getCookie('csrftoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function loadPDF(paperId, pdfUrl) {
    if (!pdfUrl) return;
    
    const url = pdfUrl;
    const canvas = document.getElementById(`pdf-canvas-${paperId}`);
    if (!canvas) return;
    
    const loadingTask = pdfjsLib.getDocument(url);
    loadingTask.promise.then(pdf => {
        pdfInstances[paperId] = pdf;
        zoomLevels[paperId] = 1.0;
        renderAllPages(paperId);
    }).catch(error => {
        console.error('Error loading PDF:', error);
        const container = document.getElementById(`pdf-scroll-container-${paperId}`);
        if (container) {
            container.innerHTML = '<div class="flex items-center justify-center h-full text-error"><p>Error loading PDF</p></div>';
        }
    });
}

function renderAllPages(paperId) {
    const pdf = pdfInstances[paperId];
    if (!pdf) return;
    
    const canvas = document.getElementById(`pdf-canvas-${paperId}`);
    const container = document.getElementById(`pdf-scroll-container-${paperId}`);
    const context = canvas.getContext('2d');
    const scale = zoomLevels[paperId] || 1.0;
    
    // Clear existing canvas
    container.innerHTML = '<div class="space-y-4 p-4" id="pages-container-' + paperId + '"></div>';
    const pagesContainer = document.getElementById(`pages-container-${paperId}`);
    
    // Update page info
    document.getElementById(`page-info-${paperId}`).textContent = `${pdf.numPages} pages`;
    
    // Render all pages
    const renderPromises = [];
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
        renderPromises.push(renderPage(paperId, pageNum, scale, pagesContainer));
    }
    
    Promise.all(renderPromises).then(() => {
        console.log('All pages rendered');
    });
}

async function renderPage(paperId, pageNum, scale, container) {
    const pdf = pdfInstances[paperId];
    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale: scale });
    
    // Create canvas for this page
    const canvas = document.createElement('canvas');
    canvas.className = 'shadow-lg mx-auto';
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    
    const context = canvas.getContext('2d');
    const renderContext = {
        canvasContext: context,
        viewport: viewport
    };
    
    await page.render(renderContext).promise;
    container.appendChild(canvas);
}

function zoomIn(paperId) {
    zoomLevels[paperId] = Math.min((zoomLevels[paperId] || 1.0) + 0.25, 3.0);
    updateZoomDisplay(paperId);
    renderAllPages(paperId);
}

function zoomOut(paperId) {
    zoomLevels[paperId] = Math.max((zoomLevels[paperId] || 1.0) - 0.25, 0.5);
    updateZoomDisplay(paperId);
    renderAllPages(paperId);
}

function updateZoomDisplay(paperId) {
    const zoomPercent = Math.round((zoomLevels[paperId] || 1.0) * 100);
    document.getElementById(`zoom-level-${paperId}`).textContent = `${zoomPercent}%`;
}

function openDecisionModal(assignmentId, decision) {
    currentAssignmentId = assignmentId;
    currentDecision = decision;
    
    const notesInput = document.getElementById('notes-' + assignmentId);
    const modalNotes = document.getElementById('modal-notes-input');
    const title = document.getElementById('modal-title');
    
    modalNotes.value = notesInput.value || '';
    
    if (decision === 'INCLUDED') {
        title.textContent = 'Include paper (Full-text)';
    } else if (decision === 'EXCLUDED') {
        title.textContent = 'Exclude paper (Full-text)';
    } else {
        title.textContent = 'Edit notes';
    }
    
    document.getElementById('decision-modal').showModal();
}

function closeDecisionModal() {
    document.getElementById('decision-modal').close();
    currentAssignmentId = null;
    currentDecision = null;
}

function saveDecisionAndNotes() {
    if (!currentAssignmentId) return;
    
    const form = document.getElementById('review-form-' + currentAssignmentId);
    const notesInput = document.getElementById('notes-' + currentAssignmentId);
    const modalNotes = document.getElementById('modal-notes-input');
    
    notesInput.value = modalNotes.value;
    
    const formData = new FormData(form);
    if (currentDecision && currentDecision !== 'PENDING') {
        formData.set('decision', currentDecision);
    }
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeDecisionModal();
            const paperParam = currentPaperId ? `?paper=${encodeURIComponent(currentPaperId)}` : '';
            window.location = window.location.pathname + paperParam;
        } else {
            alert('Failed to save: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to save decision');
    });
}

function showPaperDetail(paperId) {
    // Hide all paper viewers
    document.querySelectorAll('.pdf-viewer-content').forEach(el => {
        el.classList.add('hidden');
    });
    
    // Show selected paper
    const paperViewer = document.getElementById('paper-' + paperId);
    if (paperViewer) {
        paperViewer.classList.remove('hidden');
    }
    currentPaperId = paperId;
    
    // Update active state in list
    document.querySelectorAll('.paper-item').forEach(el => {
        el.classList.remove('bg-white', 'border-primary', 'border-l-4');
    });
    
    const paperItem = document.querySelector(`.paper-item[data-paper-id="${paperId}"]`);
    if (paperItem) {
        paperItem.classList.add('bg-white', 'border-primary', 'border-l-4');
        
        // Load PDF if not already loaded
        const pdfUrl = paperItem.dataset.pdfUrl;
        if (pdfUrl && !pdfInstances[paperId]) {
            loadPDF(paperId, pdfUrl);
        }
    }
}

// Select first paper on load
document.addEventListener('DOMContentLoaded', function() {
    const params = new URLSearchParams(window.location.search);
    const paperFromUrl = params.get('paper');
    let target = null;
    
    if (paperFromUrl) {
        target = document.querySelector(`.paper-item[data-paper-id="${paperFromUrl}"]`);
    }
    if (!target) {
        target = document.querySelector('.paper-item');
    }
    
    if (target) {
        const paperId = target.dataset.paperId;
        showPaperDetail(paperId);
    }
});

function retryDownload(studyIds) {
    const formData = new FormData();
    if (Array.isArray(studyIds)) {
        studyIds.forEach(id => formData.append('study_ids', id));
    }
    return fetch(retryUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) throw new Error(data.error || 'Retry failed');
        // update UI for any studies that now have pdf_url
        (data.statuses || []).forEach(st => {
            if (st.pdf_url) {
                const pid = st.id || st.study_id;
                const item = document.querySelector(`.paper-item[data-paper-id="${pid}"]`);
                if (item) {
                    item.dataset.pdfUrl = st.pdf_url;
                    const badge = item.querySelector('.badge');
                    if (badge) {
                        badge.classList.remove('badge-warning');
                        badge.classList.add('badge-success');
                        badge.textContent = 'PDF Available';
                    }
                }
                // If current, load now
                if (pid === currentPaperId && !pdfInstances[pid]) {
                    loadPDF(pid, st.pdf_url);
                }
            }
        });
        return data;
    });
}

function openUploadModal(studyId) {
    document.getElementById('upload-study-id').value = studyId;
    document.getElementById('upload-file').value = '';
    document.getElementById('upload-modal').showModal();
}

function closeUploadModal() {
    document.getElementById('upload-modal').close();
}

function submitUpload() {
    const studyId = document.getElementById('upload-study-id').value;
    const fileInput = document.getElementById('upload-file');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please choose a PDF file');
        return;
    }
    const fd = new FormData();
    fd.append('study_id', studyId);
    fd.append('file', file);
    fetch(uploadUrl, {
        method: 'POST',
        body: fd,
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) throw new Error(data.error || 'Upload failed');
        closeUploadModal();
        const pdfUrl = data.pdf_url;
        const item = document.querySelector(`.paper-item[data-paper-id="${studyId}"]`);
        if (item && pdfUrl) {
            item.dataset.pdfUrl = pdfUrl;
            const badge = item.querySelector('.badge');
            if (badge) {
                badge.classList.remove('badge-warning');
                badge.classList.add('badge-success');
                badge.textContent = 'PDF Available';
            }
            // Load immediately if selected
            if (studyId === currentPaperId && !pdfInstances[studyId]) {
                loadPDF(studyId, pdfUrl);
            }
        }
    })
    .catch(err => alert(err.message));
}

function downloadAllPdfs() {
    const btn = document.getElementById('download-all-btn');
    const statusEl = document.getElementById('global-download-status');
    const downloadModal = document.getElementById('download-modal');
    const downloadModalStatus = document.getElementById('download-modal-status');

    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Descargando…';
    }
    statusEl.classList.remove('hidden');
    statusEl.textContent = 'Descargando PDFs, esto puede tardar…';

    if (downloadModal) {
        if (!downloadModal.dataset.lockHandlerBound) {
            downloadModal.addEventListener('cancel', e => {
                if (downloadModal.dataset.locked === '1') {
                    e.preventDefault();
                }
            });
            downloadModal.addEventListener('close', () => {
                if (downloadModal.dataset.locked === '1') {
                    downloadModal.showModal();
                }
            });
            downloadModal.dataset.lockHandlerBound = '1';
        }
        downloadModal.dataset.locked = '1';
        if (downloadModalStatus) {
            downloadModalStatus.textContent = 'Preparando descargas, esto puede tardar unos minutos…';
        }
        downloadModal.showModal();
    }

    retryDownload([])
        .then(data => {
            const res = data.result || {};
            const total = res.total_count || 0;
            const downloaded = res.downloaded_count || 0;
            const available = res.available_count || 0;
            const failed = res.failed_count || 0;
            statusEl.textContent = `Procesados: ${total}. Descargados: ${downloaded}. Ya disponibles: ${available}. Fallidos: ${failed}.`;
            if (downloadModalStatus) {
                downloadModalStatus.textContent = 'Descargas completadas. Puedes continuar.';
            }
        })
        .catch(err => {
            statusEl.textContent = `Error: ${err.message}`;
            if (downloadModalStatus) {
                downloadModalStatus.textContent = `Error: ${err.message}`;
            }
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Descargar PDFs';
            }
            if (downloadModal) {
                downloadModal.dataset.locked = '0';
                downloadModal.close();
            }
        });
}
