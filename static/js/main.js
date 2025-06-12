// =============================================
// MAIN.JS CORREGIDO - FUNCIONALIDAD COMPLETA
// =============================================

// Configuración global
const API_URL = '/api';

// Variables globales - FORZAR COMO GLOBALES
window.allVideos = [];
window.allPlaylists = [];
window.currentPlaylistId = null;

// Hacer aliases para compatibilidad
let allVideos = window.allVideos;
let allPlaylists = window.allPlaylists;
let currentPlaylistId = window.currentPlaylistId;

// Variables para paginación de videos - GLOBAL
window.videoPagination = {
    currentPage: 1,
    pageSize: 25,
    totalItems: 0,
    totalPages: 1,
    filteredData: [],
    searchTerm: '',
    filter: 'all',
    sortField: 'title',
    sortOrder: 'asc'
};

let videoPagination = window.videoPagination;

// ===== FUNCIONES HELPER =====

function safeElementOperation(elementId, operation) {
    try {
        const element = document.getElementById(elementId);
        if (element) {
            operation(element);
            return true;
        }
        return false;
    } catch (error) {
        console.error(`Error al operar con elemento ${elementId}:`, error);
        return false;
    }
}

function isExpired(dateString) {
    if (!dateString) return false;
    try {
        const expirationDate = new Date(dateString);
        const now = new Date();
        return expirationDate < now;
    } catch (e) {
        console.error("Error al verificar expiración:", e);
        return false;
    }
}

function formatDate(dateString) {
    if (!dateString) return 'Sin fecha';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
            return 'Fecha inválida';
        }
        return date.toLocaleString();
    } catch (e) {
        console.error("Error al formatear fecha:", e);
        return 'Error de formato';
    }
}

function formatDatePagination(dateString) {
    if (!dateString) return 'Sin fecha';
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function isPlaylistActive(playlist) {
    if (!playlist) return false;
    if (playlist.is_active === false) return false;
    
    const now = new Date();
    if (playlist.start_date && new Date(playlist.start_date) > now) return false;
    if (playlist.expiration_date && isExpired(playlist.expiration_date)) return false;
    
    return true;
}

function getPlaylistStatus(playlist) {
    const now = new Date();
    
    if (!playlist.is_active) {
        return { status: 'inactive', text: 'Inactiva', class: 'bg-secondary' };
    }
    
    if (playlist.start_date && new Date(playlist.start_date) > now) {
        return { 
            status: 'scheduled', 
            text: `Programada (inicia: ${formatDate(playlist.start_date)})`, 
            class: 'bg-warning' 
        };
    }
    
    if (playlist.expiration_date && isExpired(playlist.expiration_date)) {
        return { status: 'expired', text: 'Expirada', class: 'bg-danger' };
    }
    
    return { status: 'active', text: 'Activa', class: 'bg-success' };
}

function formatPlaylistPeriod(playlist) {
    let periodText = '';
    
    if (playlist.start_date) {
        periodText += `Inicio: ${formatDate(playlist.start_date)}`;
    } else {
        periodText += 'Inicio: Inmediato';
    }
    
    if (playlist.expiration_date) {
        periodText += ` | Fin: ${formatDate(playlist.expiration_date)}`;
    } else {
        periodText += ' | Fin: Sin límite';
    }
    
    return periodText;
}

function showToast(message, type = 'success') {
    console.log(`Notificación (${type}): ${message}`);
    
    if (window.bootstrap) {
        try {
            const container = document.querySelector('.toast-container') || (() => {
                const newContainer = document.createElement('div');
                newContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(newContainer);
                return newContainer;
            })();
            
            const toastEl = document.createElement('div');
            toastEl.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0`;
            toastEl.setAttribute('role', 'alert');
            toastEl.setAttribute('aria-live', 'assertive');
            toastEl.setAttribute('aria-atomic', 'true');
            
            toastEl.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            container.appendChild(toastEl);
            
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
            
            toastEl.addEventListener('hidden.bs.toast', () => {
                toastEl.remove();
            });
        } catch (e) {
            console.error("Error al crear toast de Bootstrap:", e);
            alert(message);
        }
    } else {
        alert(message);
    }
}

// ===== FUNCIONES DE PAGINACIÓN DE VIDEOS =====

window.applyFiltersAndDisplayPage = function() {
    console.log('=== APLICANDO FILTROS ===');
    
    if (!window.allVideos) {
        console.error('window.allVideos es undefined - inicializando como array vacío');
        window.allVideos = [];
        allVideos = window.allVideos;
    }
    
    if (!Array.isArray(window.allVideos)) {
        console.error('window.allVideos no es un array - convirtiendo a array');
        window.allVideos = Array.isArray(allVideos) ? allVideos : [];
        allVideos = window.allVideos;
    }
    
    if (window.allVideos.length === 0) {
        console.warn('window.allVideos está vacío - mostrando mensaje');
        const videosList = document.getElementById('videosList');
        if (videosList) {
            videosList.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div class="text-muted">
                            <i class="fas fa-info-circle fa-3x mb-3"></i>
                            <p class="mb-0">No hay videos cargados</p>
                            <p class="small">Intenta recargar la página o verificar la conexión a la API</p>
                        </div>
                    </td>
                </tr>
            `;
        }
        return;
    }
    
    let filtered = [...window.allVideos];

    // Filtrar por estado de expiración
    if (videoPagination.filter === 'active') {
        filtered = filtered.filter(video => !video.expiration_date || new Date(video.expiration_date) >= new Date());
    } else if (videoPagination.filter === 'expired') {
        filtered = filtered.filter(video => video.expiration_date && new Date(video.expiration_date) < new Date());
    }

    // Filtrar por búsqueda
    if (videoPagination.searchTerm) {
        filtered = filtered.filter(video => 
            (video.title || '').toLowerCase().includes(videoPagination.searchTerm) ||
            (video.description || '').toLowerCase().includes(videoPagination.searchTerm)
        );
    }

    // Ordenar los datos
    filtered.sort((a, b) => {
        let aValue = a[videoPagination.sortField] || '';
        let bValue = b[videoPagination.sortField] || '';
        
        if (videoPagination.sortField.includes('date')) {
            aValue = new Date(aValue || 0);
            bValue = new Date(bValue || 0);
        } else {
            aValue = aValue.toString().toLowerCase();
            bValue = bValue.toString().toLowerCase();
        }
        
        if (videoPagination.sortOrder === 'desc') {
            return bValue > aValue ? 1 : -1;
        }
        return aValue > bValue ? 1 : -1;
    });

    videoPagination.filteredData = filtered;
    videoPagination.totalItems = filtered.length;
    videoPagination.totalPages = Math.ceil(videoPagination.totalItems / videoPagination.pageSize);
    
    // Ajustar página actual
    if (videoPagination.currentPage > videoPagination.totalPages && videoPagination.totalPages > 0) {
        videoPagination.currentPage = videoPagination.totalPages;
    }
    if (videoPagination.currentPage < 1) {
        videoPagination.currentPage = 1;
    }

    // Llamar funciones de display
    if (typeof window.displayCurrentPage === 'function') {
        window.displayCurrentPage();
    }
    if (typeof window.updatePaginationInfo === 'function') {
        window.updatePaginationInfo();
    }
    if (typeof window.updatePaginationButtons === 'function') {
        window.updatePaginationButtons();
    }
};

window.displayCurrentPage = function() {
    const startIndex = (videoPagination.currentPage - 1) * videoPagination.pageSize;
    const endIndex = Math.min(startIndex + videoPagination.pageSize, videoPagination.totalItems);
    const pageData = videoPagination.filteredData.slice(startIndex, endIndex);

    const videosList = document.getElementById('videosList');
    if (!videosList) {
        console.error('videosList no encontrado');
        return;
    }
    
    if (pageData.length === 0) {
        videosList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5">
                    <div class="text-muted">
                        <i class="fas fa-search fa-3x mb-3"></i>
                        <p class="mb-0">No se encontraron videos</p>
                        ${videoPagination.searchTerm ? '<p class="small">Intenta con otros términos de búsqueda</p>' : ''}
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    const rows = pageData.map(video => {
        const isExpired = video.expiration_date && new Date(video.expiration_date) < new Date();
        return `
            <tr class="${isExpired ? 'table-warning' : ''}">
                <td>
                    <strong>${escapeHtml(video.title || 'Sin título')}</strong>
                </td>
                <td>
                    <span class="text-muted">${escapeHtml(video.description || 'Sin descripción')}</span>
                </td>
                <td>
                    <small class="text-muted">${formatDatePagination(video.upload_date || video.created_at)}</small>
                </td>
                <td>
                    ${video.expiration_date ? 
                        `<span class="badge ${isExpired ? 'bg-danger' : 'bg-info'}">
                            ${isExpired ? 'Expirado' : 'Activo'}: ${formatDatePagination(video.expiration_date)}
                        </span>` : 
                        '<span class="text-muted">Sin expiración</span>'}
                </td>
                <td>
                    <span class="badge ${isExpired ? 'bg-danger' : 'bg-success'}">
                        ${isExpired ? 'Expirado' : 'Activo'}
                    </span>
                </td>
                <td>
                    <div class="btn-group">
                        <a href="${API_URL}/videos/${video.id}/download" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-download"></i> Descargar
                        </a>
                        <button class="btn btn-outline-secondary btn-sm" onclick="editVideo(${video.id})">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="deleteVideo(${video.id})">
                            <i class="fas fa-trash"></i> Eliminar
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    videosList.innerHTML = rows;
};

window.updatePaginationInfo = function() {
    const startItem = videoPagination.totalItems > 0 ? 
        (videoPagination.currentPage - 1) * videoPagination.pageSize + 1 : 0;
    const endItem = Math.min(videoPagination.currentPage * videoPagination.pageSize, videoPagination.totalItems);
    
    const videoCountBadge = document.getElementById('videoCountBadge');
    if (videoCountBadge) {
        videoCountBadge.textContent = `${videoPagination.totalItems} video${videoPagination.totalItems !== 1 ? 's' : ''}`;
    }
    
    const paginationInfo = document.getElementById('videoPaginationInfo');
    if (paginationInfo) {
        paginationInfo.textContent = `Mostrando ${startItem} - ${endItem} de ${videoPagination.totalItems} resultados`;
    }
};

window.updatePaginationButtons = function() {
    const firstBtn = document.getElementById('firstVideoPageBtn');
    const prevBtn = document.getElementById('prevVideoPageBtn');
    const nextBtn = document.getElementById('nextVideoPageBtn');
    const lastBtn = document.getElementById('lastVideoPageBtn');
    const pageInput = document.getElementById('videoPageInput');
    const totalPagesSpan = document.getElementById('totalVideoPages');
    const paginationFooter = document.getElementById('videoPaginationFooter');
    
    if (firstBtn) firstBtn.disabled = videoPagination.currentPage <= 1;
    if (prevBtn) prevBtn.disabled = videoPagination.currentPage <= 1;
    if (nextBtn) nextBtn.disabled = videoPagination.currentPage >= videoPagination.totalPages;
    if (lastBtn) lastBtn.disabled = videoPagination.currentPage >= videoPagination.totalPages;
    
    if (pageInput) {
        pageInput.value = videoPagination.currentPage;
        pageInput.max = videoPagination.totalPages;
    }
    
    if (totalPagesSpan) {
        totalPagesSpan.textContent = videoPagination.totalPages;
    }
    
    if (paginationFooter) {
        const startItem = videoPagination.totalItems > 0 ?
            (videoPagination.currentPage - 1) * videoPagination.pageSize + 1 : 0;
        const endItem = Math.min(videoPagination.currentPage * videoPagination.pageSize, videoPagination.totalItems);
        paginationFooter.innerHTML = `
            Página ${videoPagination.currentPage} de ${videoPagination.totalPages} 
            <span class="text-primary">(${startItem}-${endItem} de ${videoPagination.totalItems})</span>
        `;
    }
};

// ===== FUNCIONES DE NAVEGACIÓN =====

window.goToVideoPage = function(page) {
    page = parseInt(page);
    if (page >= 1 && page <= videoPagination.totalPages && page !== videoPagination.currentPage) {
        videoPagination.currentPage = page;
        displayCurrentPage();
        updatePaginationInfo();
        updatePaginationButtons();
    }
};

window.goToFirstVideoPage = function() {
    window.goToVideoPage(1);
};

window.goToPrevVideoPage = function() {
    if (videoPagination.currentPage > 1) {
        window.goToVideoPage(videoPagination.currentPage - 1);
    }
};

window.goToNextVideoPage = function() {
    if (videoPagination.currentPage < videoPagination.totalPages) {
        window.goToVideoPage(videoPagination.currentPage + 1);
    }
};

window.goToLastVideoPage = function() {
    window.goToVideoPage(videoPagination.totalPages);
};

window.sortVideoTable = function(field) {
    if (videoPagination.sortField === field) {
        videoPagination.sortOrder = videoPagination.sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        videoPagination.sortField = field;
        videoPagination.sortOrder = 'asc';
    }
    
    applyFiltersAndDisplayPage();
    
    // Actualizar iconos de ordenamiento
    document.querySelectorAll('#videosTable th .fas').forEach(icon => {
        icon.className = 'fas fa-sort ms-1';
    });
    
    const currentButton = document.querySelector(`button[onclick="sortVideoTable('${field}')"] .fas`);
    if (currentButton) {
        currentButton.className = `fas fa-sort-${videoPagination.sortOrder === 'asc' ? 'up' : 'down'} ms-1`;
    }
};

// ===== GESTIÓN DE VIDEOS =====

window.loadVideos = async function(filter = 'all') {
    console.log('=== CARGANDO VIDEOS ===');
    
    const videosList = document.getElementById('videosList');
    if (!videosList) {
        console.error("Elemento videosList no encontrado");
        return;
    }
    
    try {
        // Mostrar indicador de carga
        videosList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-3">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Cargando videos...</p>
                </td>
            </tr>
        `;
        
        // Cargar videos desde la API
        const response = await fetch(`${API_URL}/videos/`);
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }
        
        const responseData = await response.json();
        
        // ASIGNAR A VARIABLE GLOBAL
        window.allVideos = Array.isArray(responseData) ? responseData : responseData.items || [];
        allVideos = window.allVideos;
        
        console.log(`Videos cargados en window.allVideos: ${window.allVideos.length}`);
        
        // Verificar que se cargaron correctamente
        if (!Array.isArray(window.allVideos)) {
            throw new Error('Los datos recibidos no son un array válido');
        }
        
        // Aplicar filtro inicial
        videoPagination.filter = filter;
        videoPagination.currentPage = 1;
        
        // Aplicar filtros DESPUÉS de asegurar que allVideos existe
        setTimeout(() => {
            window.applyFiltersAndDisplayPage();
        }, 100);
        
        console.log('=== VIDEOS CARGADOS CORRECTAMENTE ===');
        
    } catch (error) {
        console.error('Error al cargar videos:', error);
        videosList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5">
                    <div class="alert alert-danger mb-0">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error al cargar videos: ${error.message}
                        <br><small>Verifica la conexión a la API en: ${API_URL}/videos/</small>
                    </div>
                </td>
            </tr>
        `;
        
        // Inicializar array vacío en caso de error
        window.allVideos = [];
        allVideos = window.allVideos;
    }
};



async function uploadVideo(formData) {
    const progressBar = document.querySelector('#uploadProgress .progress-bar');
    const progressContainer = document.getElementById('uploadProgress');
    
    if (progressContainer) {
        progressContainer.classList.remove('d-none');
    }
    
    try {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', `${API_URL}/videos/`, true);
            
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable && progressBar) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percentComplete + '%';
                    progressBar.textContent = percentComplete + '%';
                    progressBar.setAttribute('aria-valuenow', percentComplete);
                }
            };
            
            xhr.onload = () => {
                if (xhr.status === 200 || xhr.status === 201) {
                    showToast('Video subido correctamente', 'success');
                    
                    safeElementOperation('videoUploadForm', form => {
                        form.reset();
                    });
                    
                    const uploadForm = document.getElementById('uploadForm');
                    if (uploadForm && window.bootstrap) {
                        try {
                            const collapse = bootstrap.Collapse.getInstance(uploadForm);
                            if (collapse) {
                                collapse.hide();
                            }
                        } catch (e) {
                            console.error("Error al ocultar formulario:", e);
                        }
                    }
                    
                    setTimeout(() => {
                        loadVideos();
                    }, 500);
                    
                    resolve();
                } else {
                    let errorMessage = 'Error al subir el video';
                    try {
                        const response = JSON.parse(xhr.responseText);
                        errorMessage = response.detail || errorMessage;
                    } catch (e) {}
                    showToast(errorMessage, 'error');
                    reject(new Error(errorMessage));
                }
                
                if (progressContainer) {
                    progressContainer.classList.add('d-none');
                }
            };
            
            xhr.onerror = () => {
                const errorMsg = 'Error de red al intentar subir el video';
                showToast(errorMsg, 'error');
                
                if (progressContainer) {
                    progressContainer.classList.add('d-none');
                }
                
                reject(new Error(errorMsg));
            };
            
            xhr.send(formData);
        });
    } catch (error) {
        console.error('Error al subir video:', error);
        showToast(`Error al subir el video: ${error.message}`, 'error');
        
        if (progressContainer) {
            progressContainer.classList.add('d-none');
        }
    }
}

async function editVideo(videoId) {
    console.log("Editando video:", videoId);
    
    try {
        const video = allVideos.find(v => v.id === videoId);
        if (!video) {
            throw new Error('Video no encontrado en los datos cargados');
        }
        
        const editIdInput = document.getElementById('editVideoId');
        const editTitleInput = document.getElementById('editVideoTitle');
        const editDescriptionInput = document.getElementById('editVideoDescription');
        const editExpirationInput = document.getElementById('editVideoExpiration');
        
        if (!editIdInput || !editTitleInput || !editDescriptionInput || !editExpirationInput) {
            throw new Error('No se encontraron todos los elementos del formulario de edición');
        }
        
        editIdInput.value = video.id;
        editTitleInput.value = video.title || '';
        editDescriptionInput.value = video.description || '';
        
        if (video.expiration_date) {
            try {
                const date = new Date(video.expiration_date);
                if (!isNaN(date.getTime())) {
                    const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                        .toISOString()
                        .slice(0, 16);
                    editExpirationInput.value = localDatetime;
                } else {
                    editExpirationInput.value = '';
                }
            } catch (e) {
                console.error("Error al procesar fecha de expiración:", e);
                editExpirationInput.value = '';
            }
        } else {
            editExpirationInput.value = '';
        }
        
        const editModal = document.getElementById('editVideoModal');
        if (!editModal) {
            throw new Error('No se encontró el modal de edición de videos');
        }
        
        if (window.bootstrap) {
            try {
                const modal = new bootstrap.Modal(editModal);
                modal.show();
            } catch (e) {
                console.error("Error al mostrar modal:", e);
                throw new Error('Error al mostrar el modal de edición: ' + e.message);
            }
        } else {
            throw new Error('Bootstrap no está disponible para mostrar el modal');
        }
        
    } catch (error) {
        console.error('Error al preparar el video para edición:', error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function saveVideoChanges() {
    console.log("Guardando cambios de video...");
    
    try {
        const videoIdInput = document.getElementById('editVideoId');
        const titleInput = document.getElementById('editVideoTitle');
        const descriptionInput = document.getElementById('editVideoDescription');
        const expirationInput = document.getElementById('editVideoExpiration');
        
        if (!videoIdInput || !titleInput || !descriptionInput || !expirationInput) {
            throw new Error('Elementos del formulario no encontrados');
        }
        
        const videoId = videoIdInput.value;
        const title = titleInput.value;
        const description = descriptionInput.value;
        const expirationDate = expirationInput.value;
        
        if (!videoId) {
            throw new Error('ID de video no válido');
        }
        
        if (!title) {
            throw new Error('El título no puede estar vacío');
        }
        
        const response = await fetch(`${API_URL}/videos/${videoId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title,
                description,
                expiration_date: expirationDate || null
            }),
        });
        
        if (!response.ok) {
            let errorMessage = `Error (${response.status}): ${response.statusText}`;
            
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch (e) {}
            
            throw new Error(errorMessage);
        }
        
        if (window.bootstrap) {
            try {
                const modalElement = document.getElementById('editVideoModal');
                if (modalElement) {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) {
                        modal.hide();
                    }
                }
            } catch (e) {
                console.error("Error al cerrar modal:", e);
            }
        }
        
        showToast('Video actualizado correctamente', 'success');
        
        setTimeout(() => {
            loadVideos();
        }, 500);
        
    } catch (error) {
        console.error('Error al guardar cambios del video:', error);
        showToast(`Error al guardar cambios: ${error.message}`, 'error');
    }
}

async function deleteVideo(videoId) {
    if (!confirm('¿Estás seguro de que deseas eliminar este video? Esta acción no se puede deshacer.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/videos/${videoId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al eliminar el video');
        }
        
        showToast('Video eliminado correctamente', 'success');
        
        setTimeout(() => {
            loadVideos();
        }, 500);
        
    } catch (error) {
        console.error('Error al eliminar video:', error);
        showToast(`Error al eliminar el video: ${error.message}`, 'error');
    }
}

// ===== GESTIÓN DE PLAYLISTS =====

async function loadPlaylists(filter = 'all') {
    console.log("Cargando playlists con filtro:", filter);
    
    const playlistsList = document.getElementById('playlistsList');
    if (!playlistsList) {
        console.error("Elemento playlistsList no encontrado");
        return;
    }
    
    try {
        playlistsList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-3">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Cargando listas de reproducción...</p>
                </td>
            </tr>
        `;
        
        const response = await fetch(`${API_URL}/playlists/`);
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }
        
        allPlaylists = await response.json();
        
        if (!Array.isArray(allPlaylists)) {
            throw new Error("Formato de datos inválido");
        }
        
        let filteredPlaylists = allPlaylists;
        if (filter === 'active') {
            filteredPlaylists = allPlaylists.filter(playlist => isPlaylistActive(playlist));
        } else if (filter === 'inactive') {
            filteredPlaylists = allPlaylists.filter(playlist => !isPlaylistActive(playlist));
        }
        
        safeElementOperation('playlistCountBadge', element => {
            element.textContent = `${filteredPlaylists.length} listas`;
        });
        
        let playlistsHTML = '';
        
        if (filteredPlaylists.length === 0) {
            playlistsHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <p>No hay listas de reproducción disponibles. ¡Crea tu primera lista!</p>
                    </td>
                </tr>
            `;
        } else {
            filteredPlaylists.forEach(playlist => {
                const statusInfo = getPlaylistStatus(playlist);
                const periodText = formatPlaylistPeriod(playlist);
                    
                playlistsHTML += `
                    <tr class="${statusInfo.status === 'active' ? '' : 'table-warning'}">
                        <td>${playlist.title || ''}</td>
                        <td>${playlist.description || '<span class="text-muted">Sin descripción</span>'}</td>
                        <td>
                            <span class="badge bg-secondary">${playlist.videos ? playlist.videos.length : 0} videos</span>
                        </td>
                        <td>
                            <small class="text-muted">${periodText}</small>
                        </td>
                        <td>
                            <span class="badge ${statusInfo.class}">
                                ${statusInfo.text}
                            </span>
                        </td>
                        <td>
                            <button class="btn btn-primary btn-sm" onclick="openPlaylistDetail(${playlist.id})">
                                <i class="fas fa-eye"></i> Ver Detalles
                            </button>
                        </td>
                    </tr>
                `;
            });
        }
        
        playlistsList.innerHTML = playlistsHTML;
        
    } catch (error) {
        console.error('Error al cargar playlists:', error);
        
        if (playlistsList) {
            playlistsList.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div class="alert alert-danger">Error al cargar listas de reproducción: ${error.message}</div>
                    </td>
                </tr>
            `;
        }
        
        showToast(`Error al cargar listas de reproducción: ${error.message}`, 'error');
    }
}

async function createPlaylist(playlistData) {
    try {
        const formData = {
            title: document.getElementById('playlistTitle')?.value || '',
            description: document.getElementById('playlistDescription')?.value || null,
            start_date: document.getElementById('playlistStartDate')?.value || null,
            expiration_date: document.getElementById('playlistExpiration')?.value || null,
            is_active: document.getElementById('playlistActive')?.checked || false
        };
        
        const response = await fetch(`${API_URL}/playlists/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al crear la lista');
        }
        
        showToast('Lista de reproducción creada correctamente', 'success');
        
        safeElementOperation('playlistCreateForm', form => {
            form.reset();
        });
        
        if (window.bootstrap) {
            try {
                const playlistForm = document.getElementById('playlistForm');
                if (playlistForm) {
                    const collapse = bootstrap.Collapse.getInstance(playlistForm);
                    if (collapse) {
                        collapse.hide();
                    }
                }
            } catch (e) {
                console.error("Error al ocultar formulario:", e);
            }
        }
        
        setTimeout(() => {
            loadPlaylists();
        }, 500);
        
    } catch (error) {
        console.error('Error al crear playlist:', error);
        showToast(`Error al crear la lista de reproducción: ${error.message}`, 'error');
    }
}

function filterPlaylistsByTitle(searchText) {
    searchText = (searchText || '').toLowerCase().trim();
    
    const playlistsList = document.getElementById('playlistsList');
    if (!playlistsList) {
        console.error("Elemento playlistsList no encontrado");
        return;
    }
    
    try {
        if (!searchText) {
            const filterSelect = document.getElementById('playlistFilterStatus');
            const currentFilter = filterSelect ? filterSelect.value : 'all';
            loadPlaylists(currentFilter);
            return;
        }
        
        const filteredPlaylists = allPlaylists.filter(playlist => 
            (playlist.title && playlist.title.toLowerCase().includes(searchText)) ||
            (playlist.description && playlist.description.toLowerCase().includes(searchText))
        );
        
        safeElementOperation('playlistCountBadge', element => {
            element.textContent = `${filteredPlaylists.length} listas`;
        });
        
        let playlistsHTML = '';
        
        if (filteredPlaylists.length === 0) {
            playlistsHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <p>No se encontraron listas con esos criterios de búsqueda.</p>
                    </td>
                </tr>
            `;
        } else {
            filteredPlaylists.forEach(playlist => {
                const active = isPlaylistActive(playlist);
                const expirationText = playlist.expiration_date 
                    ? `${isExpired(playlist.expiration_date) ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`
                    : 'Sin fecha de expiración';
                    
                playlistsHTML += `
                    <tr class="${active ? '' : 'table-danger'}">
                        <td>${playlist.title || ''}</td>
                        <td>${playlist.description || '<span class="text-muted">Sin descripción</span>'}</td>
                        <td>
                            <span class="badge bg-secondary">${playlist.videos ? playlist.videos.length : 0} videos</span>
                        </td>
                        <td>
                            <span class="badge bg-info">${expirationText}</span>
                        </td>
                        <td>
                            <span class="badge ${active ? 'bg-success' : 'bg-danger'}">
                                ${active ? 'Activa' : 'Inactiva'}
                            </span>
                        </td>
                        <td>
                            <button class="btn btn-primary btn-sm" onclick="openPlaylistDetail(${playlist.id})">
                                <i class="fas fa-eye"></i> Ver Detalles
                            </button>
                        </td>
                    </tr>
                `;
            });
        }
        
        playlistsList.innerHTML = playlistsHTML;
        
    } catch (error) {
        console.error('Error al filtrar playlists:', error);
        showToast(`Error al filtrar listas: ${error.message}`, 'error');
    }
}

// ===== FUNCIÓN PRINCIPAL PARA ABRIR DETALLES DE PLAYLIST =====
window.openPlaylistDetail = async function(playlistId) {
    currentPlaylistId = playlistId;
    try {
        console.log(`Abriendo detalles de playlist ${playlistId}`);
        
        const response = await fetch(`${API_URL}/playlists/${playlistId}`);
        if (!response.ok) throw new Error('Error al cargar detalles de la playlist');
        
        const playlist = await response.json();
        console.log('Playlist cargada:', playlist);
        
        // Mostrar información básica de la playlist
        document.getElementById('playlistDetailTitle').textContent = playlist.title;
        document.getElementById('playlistDetailDescription').textContent = playlist.description || 'Sin descripción';
        document.getElementById('playlistDetailDate').textContent = `Creada: ${formatDate(playlist.creation_date)}`;
        
        // Mostrar fecha de expiración
        const expirationBadge = document.getElementById('playlistDetailExpirationDate');
        if (playlist.expiration_date) {
            const expired = isExpired(playlist.expiration_date);
            expirationBadge.className = `badge ${expired ? 'bg-danger' : 'bg-info'}`;
            expirationBadge.textContent = `${expired ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`;
        } else {
            expirationBadge.className = 'badge bg-secondary';
            expirationBadge.textContent = 'Sin fecha de expiración';
        }
        
        // Mostrar estado de la playlist
        const statusBadge = document.getElementById('playlistDetailStatus');
        const isActive = isPlaylistActive(playlist);
        statusBadge.className = `badge ${isActive ? 'bg-success' : 'bg-danger'}`;
        statusBadge.textContent = isActive ? 'Activa' : 'Inactiva';
        
        // Configurar botón de descarga
        document.getElementById('playlistDownloadBtn').onclick = () => {
            window.location.href = `${API_URL}/playlists/${playlistId}/download`;
        };
        
        // Configurar botón de editar
        document.getElementById('editPlaylistBtn').onclick = () => {
            preparePlaylistForEditing(playlist);
        };
        
        // Configurar botón de eliminar
        document.getElementById('deletePlaylistBtn').onclick = () => {
            if (confirm('¿Estás seguro de que deseas eliminar esta lista de reproducción?')) {
                deletePlaylist(playlistId);
            }
        };
        
        // Mostrar videos en la playlist
        displayPlaylistVideos(playlist);
        
        // Cargar videos disponibles para agregar
        await loadAvailableVideos(playlistId, playlist);
        
        // Configurar botón para agregar video
        document.getElementById('addVideoBtn').onclick = () => {
            const videoId = document.getElementById('addVideoSelect').value;
            if (videoId) {
                addVideoToPlaylist(playlistId, parseInt(videoId));
            } else {
                showToast('Por favor, selecciona un video para agregar a la lista', 'error');
            }
        };
        
        // Cargar dispositivos asignados
        await loadPlaylistDevices(playlistId);
        await loadAvailableDevices(playlistId);
        
        // Configurar botón para agregar dispositivo
        document.getElementById('addDeviceBtn').onclick = () => {
            const deviceId = document.getElementById('addDeviceSelect').value;
            if (deviceId) {
                addDeviceToPlaylist(playlistId, deviceId);
            } else {
                showToast('Por favor, selecciona un dispositivo para asignar a la lista', 'error');
            }
        };
        
        // Mostrar el modal
        const modal = new bootstrap.Modal(document.getElementById('playlistDetailModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error al cargar detalles de la playlist:', error);
        showToast(`Error al cargar los detalles de la lista de reproducción: ${error.message}`, 'error');
    }
};

// ===== FUNCIONES PARA MOSTRAR VIDEOS EN PLAYLIST =====
function displayPlaylistVideos(playlist) {
    const playlistVideos = document.getElementById('playlistVideos');
    playlistVideos.innerHTML = '';
    
    if (!playlist.videos || playlist.videos.length === 0) {
        playlistVideos.innerHTML = '<tr><td colspan="4" class="text-center">No hay videos en esta lista</td></tr>';
        return;
    }
    
    playlist.videos.forEach(video => {
        const videoExpired = video.expiration_date && isExpired(video.expiration_date);
        const videoRow = document.createElement('tr');
        videoRow.className = videoExpired ? 'table-danger' : '';
        
        videoRow.innerHTML = `
            <td>${escapeHtml(video.title || 'Sin título')}</td>
            <td>${escapeHtml(video.description || 'Sin descripción')}</td>
            <td>
                ${video.expiration_date ? 
                    `<span class="badge ${videoExpired ? 'bg-danger' : 'bg-info'}">
                        ${videoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                    </span>` : 
                    '<span class="text-muted">Sin expiración</span>'}
            </td>
            <td>
                <button class="btn btn-outline-danger btn-sm" onclick="removeVideoFromPlaylist(${playlist.id}, ${video.id})">
                    <i class="fas fa-times"></i> Eliminar
                </button>
            </td>
        `;
        playlistVideos.appendChild(videoRow);
    });
}

// ===== FUNCIONES PARA CARGAR VIDEOS DISPONIBLES =====
async function loadAvailableVideos(playlistId, playlist) {
    const addVideoSelect = document.getElementById('addVideoSelect');
    if (!addVideoSelect) {
        console.error("No se encontró el select para añadir videos");
        return;
    }
    
    try {
        addVideoSelect.innerHTML = '<option value="">Cargando videos...</option>';
        
        // Asegurarnos de que allVideos esté disponible
        if (!allVideos || allVideos.length === 0) {
            try {
                const response = await fetch(`${API_URL}/videos/`);
                if (response.ok) {
                    allVideos = await response.json();
                    window.allVideos = allVideos; // Actualizar variable global
                } else {
                    throw new Error(`Error al cargar videos: ${response.status} ${response.statusText}`);
                }
            } catch (err) {
                console.error("Error al cargar videos:", err);
                addVideoSelect.innerHTML = '<option value="">Error al cargar videos disponibles</option>';
                return;
            }
        }
        
        // Resetear el select
        addVideoSelect.innerHTML = '<option value="">Seleccionar video...</option>';
        
        // Filtrar videos que no están en la playlist y que no han expirado
        if (allVideos && allVideos.length > 0) {
            const playlistVideoIds = new Set((playlist.videos || []).map(v => v.id));
            const availableVideos = allVideos.filter(video => 
                !playlistVideoIds.has(video.id) && 
                (!video.expiration_date || !isExpired(video.expiration_date))
            );
            
            if (availableVideos.length === 0) {
                addVideoSelect.innerHTML += '<option disabled>No hay videos disponibles para agregar</option>';
            } else {
                // Añadir cada video disponible al select
                availableVideos.forEach(video => {
                    const option = document.createElement('option');
                    option.value = video.id;
                    option.textContent = video.title || `Video ${video.id}`;
                    addVideoSelect.appendChild(option);
                });
            }
        } else {
            addVideoSelect.innerHTML += '<option disabled>No hay videos disponibles</option>';
        }
    } catch (error) {
        console.error('Error al cargar videos disponibles:', error);
        addVideoSelect.innerHTML = '<option value="">Error al cargar videos disponibles</option>';
    }
}

// ===== FUNCIONES PARA AGREGAR/ELIMINAR VIDEOS =====
async function addVideoToPlaylist(playlistId, videoId) {
    try {
        console.log(`Agregando video ${videoId} a playlist ${playlistId}`);
        
        const response = await fetch(`${API_URL}/playlists/${playlistId}/videos/${videoId}`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al añadir el video');
        }
        
        showToast('Video añadido a la lista correctamente', 'success');
        
        // Recargar detalles de la playlist
        setTimeout(() => {
            openPlaylistDetail(playlistId);
        }, 500);
        
    } catch (error) {
        console.error('Error al añadir video a playlist:', error);
        showToast(`Error al añadir el video a la lista: ${error.message}`, 'error');
    }
}

window.removeVideoFromPlaylist = async function(playlistId, videoId) {
    if (!confirm('¿Estás seguro de que deseas eliminar este video de la lista de reproducción?')) {
        return;
    }
    
    try {
        console.log(`Eliminando video ${videoId} de playlist ${playlistId}`);
        
        const response = await fetch(`${API_URL}/playlists/${playlistId}/videos/${videoId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al eliminar el video');
        }
        
        showToast('Video eliminado de la lista correctamente', 'success');
        
        // Recargar detalles de la playlist
        setTimeout(() => {
            openPlaylistDetail(playlistId);
        }, 500);
        
    } catch (error) {
        console.error('Error al eliminar video de playlist:', error);
        showToast(`Error al eliminar el video de la lista: ${error.message}`, 'error');
    }
};

// ===== FUNCIONES PARA CARGAR DISPOSITIVOS =====
async function loadPlaylistDevices(playlistId) {
    console.log("Cargando dispositivos para playlist:", playlistId);

    const devicesContainer = document.getElementById('assignedDevicesContainer');
    if (!devicesContainer) {
        console.error("No se encontró el contenedor de dispositivos asignados");
        return;
    }
    
    try {
        devicesContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <span class="ms-2">Cargando dispositivos asignados...</span>
            </div>
        `;

        const response = await fetch(`${API_URL}/device-playlists/playlist/${playlistId}/devices`);
        
        if (!response.ok) {
            throw new Error(`Error al cargar dispositivos asignados: ${response.status} ${response.statusText}`);
        }
        
        const assignedDevices = await response.json();
        console.log("Dispositivos asignados recibidos:", assignedDevices);
        
        if (!assignedDevices || assignedDevices.length === 0) {
            devicesContainer.innerHTML = '<p class="text-center">No hay dispositivos asignados a esta lista</p>';
            return;
        }
        
        const tableHTML = `
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Nombre</th>
                        <th>Ubicación</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    ${assignedDevices.map(device => `
                        <tr class="${device.is_active ? '' : 'table-warning'}">
                            <td>${device.device_id}</td>
                            <td>${device.name || 'Sin nombre'}</td>
                            <td>${device.location || ''} ${device.tienda ? ' - ' + device.tienda : ''}</td>
                            <td>
                                <span class="badge ${device.is_active ? 'bg-success' : 'bg-danger'}">
                                    ${device.is_active ? 'Activo' : 'Inactivo'}
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-outline-danger btn-sm" onclick="removeDeviceFromPlaylist('${device.device_id}', ${playlistId})">
                                    <i class="fas fa-times"></i> Eliminar
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        devicesContainer.innerHTML = tableHTML;
        
    } catch (error) {
        console.error('Error al cargar dispositivos asignados:', error);
        devicesContainer.innerHTML = `<div class="alert alert-danger">Error al cargar dispositivos: ${error.message}</div>`;
    }
}

async function loadAvailableDevices(playlistId) {
    console.log("Cargando dispositivos disponibles para playlist:", playlistId);
    
    try {
        // Obtener todos los dispositivos activos
        const allDevicesResponse = await fetch(`${API_URL}/devices/?active_only=true`);
        if (!allDevicesResponse.ok) {
            throw new Error(`Error al cargar dispositivos: ${allDevicesResponse.status} ${allDevicesResponse.statusText}`);
        }
        const allDevices = await allDevicesResponse.json();
        
        // Obtener dispositivos ya asignados
        const assignedDevicesResponse = await fetch(`${API_URL}/device-playlists/playlist/${playlistId}/devices`);
        if (!assignedDevicesResponse.ok) {
            throw new Error(`Error al cargar dispositivos asignados: ${assignedDevicesResponse.status} ${assignedDevicesResponse.statusText}`);
        }
        const assignedDevices = await assignedDevicesResponse.json();
        
        // Filtrar dispositivos que no están asignados
        const assignedDeviceIds = new Set(assignedDevices.map(d => d.device_id));
        const availableDevices = allDevices.filter(device => !assignedDeviceIds.has(device.device_id));
        
        // Actualizar el select de dispositivos disponibles
        safeElementOperation('addDeviceSelect', element => {
            element.innerHTML = '<option value="">Seleccionar dispositivo...</option>';
            
            if (availableDevices.length === 0) {
                element.innerHTML += '<option disabled>No hay dispositivos disponibles para asignar</option>';
            } else {
                availableDevices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.device_id;
                    option.textContent = `${device.name || 'Sin nombre'} (${device.device_id})`;
                    if (device.location || device.tienda) {
                        option.textContent += ` - ${device.location || ''} ${device.tienda ? ' - ' + device.tienda : ''}`;
                    }
                    element.appendChild(option);
                });
            }
        });
        
    } catch (error) {
        console.error('Error al cargar dispositivos disponibles:', error);
        safeElementOperation('addDeviceSelect', element => {
            element.innerHTML = '<option value="">Error al cargar dispositivos</option>';
        });
    }
}

// ===== FUNCIONES PARA AGREGAR/ELIMINAR DISPOSITIVOS =====
async function addDeviceToPlaylist(playlistId, deviceId) {
    try {
        console.log(`Asignando dispositivo ${deviceId} a playlist ${playlistId}`);
        
        const response = await fetch(`${API_URL}/device-playlists/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_id: deviceId,
                playlist_id: parseInt(playlistId)
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Error al asignar el dispositivo: ${response.status}`);
        }
        
        showToast('Dispositivo asignado correctamente a la lista', 'success');
        
        // Recargar los dispositivos asignados y disponibles
        setTimeout(() => {
            loadPlaylistDevices(playlistId);
            loadAvailableDevices(playlistId);
        }, 500);
        
    } catch (error) {
        console.error('Error al asignar dispositivo a playlist:', error);
        showToast(`Error al asignar el dispositivo a la lista: ${error.message}`, 'error');
    }
}

window.removeDeviceFromPlaylist = async function(deviceId, playlistId) {
    console.log(`Eliminando dispositivo ${deviceId} de playlist ${playlistId}`);
    
    try {
        if (!playlistId || !deviceId) {
            throw new Error("Faltan datos para la eliminación");
        }
        
        const response = await fetch(`${API_URL}/device-playlists/${deviceId}/${playlistId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Error al eliminar la asignación: ${response.status} ${response.statusText}`);
        }
        
        showToast('Dispositivo eliminado de la lista correctamente', 'success');
        
        // Recargar los dispositivos
        setTimeout(() => {
            loadPlaylistDevices(playlistId);
            loadAvailableDevices(playlistId);
        }, 500);
        
    } catch (error) {
        console.error('Error al eliminar dispositivo de playlist:', error);
        showToast(`Error al eliminar el dispositivo de la lista: ${error.message}`, 'error');
    }
};

// ===== FUNCIONES PARA EDITAR PLAYLIST =====
// ===== FUNCIONES CORREGIDAS PARA EDICIÓN DE PLAYLISTS =====

// Función corregida para preparar playlist para edición
window.preparePlaylistForEditing = function(playlist) {
    console.log("=== PREPARANDO PLAYLIST PARA EDICIÓN ===");
    console.log("Playlist recibida:", playlist);
    
    try {
        // Verificar que existan los elementos necesarios
        const editIdInput = document.getElementById('editPlaylistId');
        const editTitleInput = document.getElementById('editPlaylistTitle');
        const editDescriptionInput = document.getElementById('editPlaylistDescription');
        const editStartDateInput = document.getElementById('editPlaylistStartDate');
        const editExpirationInput = document.getElementById('editPlaylistExpiration');
        const editActiveCheckbox = document.getElementById('editPlaylistActive');
        
        console.log('Elementos del formulario encontrados:', {
            editIdInput: !!editIdInput,
            editTitleInput: !!editTitleInput,
            editDescriptionInput: !!editDescriptionInput,
            editStartDateInput: !!editStartDateInput,
            editExpirationInput: !!editExpirationInput,
            editActiveCheckbox: !!editActiveCheckbox
        });
        
        if (!editIdInput || !editTitleInput || !editDescriptionInput || !editExpirationInput || !editActiveCheckbox) {
            throw new Error('No se encontraron todos los campos del formulario de edición');
        }
        
        // Asignar valores a los campos
        editIdInput.value = playlist.id;
        editTitleInput.value = playlist.title || '';
        editDescriptionInput.value = playlist.description || '';
        
        console.log('Valores básicos asignados:', {
            id: editIdInput.value,
            title: editTitleInput.value,
            description: editDescriptionInput.value
        });
        
        // Formatear fecha de inicio para el input datetime-local
        if (playlist.start_date && editStartDateInput) {
            try {
                const date = new Date(playlist.start_date);
                if (!isNaN(date.getTime())) {
                    const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                        .toISOString()
                        .slice(0, 16);
                    editStartDateInput.value = localDatetime;
                    console.log('Fecha de inicio configurada:', localDatetime);
                } else {
                    editStartDateInput.value = '';
                    console.log('Fecha de inicio inválida, campo vacío');
                }
            } catch (e) {
                console.error("Error al procesar fecha de inicio:", e);
                editStartDateInput.value = '';
            }
        } else if (editStartDateInput) {
            editStartDateInput.value = '';
            console.log('Sin fecha de inicio');
        }
        
        // Formatear fecha de expiración para el input datetime-local
        if (playlist.expiration_date) {
            try {
                const date = new Date(playlist.expiration_date);
                if (!isNaN(date.getTime())) {
                    const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                        .toISOString()
                        .slice(0, 16);
                    editExpirationInput.value = localDatetime;
                    console.log('Fecha de expiración configurada:', localDatetime);
                } else {
                    editExpirationInput.value = '';
                    console.log('Fecha de expiración inválida, campo vacío');
                }
            } catch (e) {
                console.error("Error al procesar fecha de expiración:", e);
                editExpirationInput.value = '';
            }
        } else {
            editExpirationInput.value = '';
            console.log('Sin fecha de expiración');
        }
        
        editActiveCheckbox.checked = playlist.is_active || false;
        console.log('Checkbox activa configurado:', editActiveCheckbox.checked);
        
        // Manejar modales
        const detailModal = document.getElementById('playlistDetailModal');
        const editModal = document.getElementById('editPlaylistModal');
        
        console.log('Modales encontrados:', {
            detailModal: !!detailModal,
            editModal: !!editModal
        });
        
        if (!editModal) {
            throw new Error("No se encontró el modal de edición");
        }
        
        // Cerrar modal de detalles si está abierto
        if (detailModal && window.bootstrap) {
            try {
                const detailModalInstance = bootstrap.Modal.getInstance(detailModal);
                if (detailModalInstance) {
                    console.log('Cerrando modal de detalles...');
                    detailModalInstance.hide();
                }
            } catch (e) {
                console.error("Error al cerrar modal de detalles:", e);
            }
        }
        
        // Mostrar modal de edición
        console.log('Intentando mostrar modal de edición...');
        
        if (window.bootstrap) {
            try {
                // Pequeño delay para asegurar que el modal anterior se cierre completamente
                setTimeout(() => {
                    const editModalInstance = new bootstrap.Modal(editModal, {
                        backdrop: 'static', // Evitar que se cierre al hacer clic fuera
                        keyboard: true
                    });
                    editModalInstance.show();
                    console.log('Modal de edición mostrado exitosamente');
                    
                    // Enfocar el primer campo
                    setTimeout(() => {
                        editTitleInput.focus();
                    }, 300);
                    
                }, 300);
            } catch (e) {
                console.error("Error al mostrar modal de edición:", e);
                showToast("Error al abrir el formulario de edición: " + e.message, 'error');
            }
        } else {
            throw new Error('Bootstrap no está disponible');
        }
        
        console.log('=== PLAYLIST PREPARADA EXITOSAMENTE ===');
        
    } catch (error) {
        console.error("=== ERROR AL PREPARAR PLAYLIST ===", error);
        showToast(`Error: ${error.message}`, 'error');
    }
};

// Función corregida para guardar cambios de playlist
window.savePlaylistChanges = async function() {
    console.log("=== GUARDANDO CAMBIOS DE PLAYLIST ===");
    
    try {
        const editIdInput = document.getElementById('editPlaylistId');
        if (!editIdInput || !editIdInput.value) {
            throw new Error("No se ha definido ID de playlist para editar");
        }
        
        const playlistId = editIdInput.value;
        console.log('ID de playlist a editar:', playlistId);
        
        // Obtener los valores del formulario
        const editTitleInput = document.getElementById('editPlaylistTitle');
        const editDescriptionInput = document.getElementById('editPlaylistDescription');
        const editStartDateInput = document.getElementById('editPlaylistStartDate');
        const editExpirationInput = document.getElementById('editPlaylistExpiration');
        const editActiveCheckbox = document.getElementById('editPlaylistActive');
        
        if (!editTitleInput || !editDescriptionInput || !editExpirationInput || !editActiveCheckbox) {
            throw new Error("No se encontraron todos los campos del formulario");
        }
        
        // Validar datos
        const title = editTitleInput.value.trim();
        if (!title) {
            throw new Error("El título no puede estar vacío");
        }
        
        const playlistData = {
            title: title,
            description: editDescriptionInput.value.trim() || null,
            start_date: editStartDateInput ? (editStartDateInput.value || null) : null,
            expiration_date: editExpirationInput.value || null,
            is_active: editActiveCheckbox.checked
        };
        
        console.log("Datos a enviar:", playlistData);
        
        // Mostrar indicador de carga en el botón
        const saveBtn = document.getElementById('savePlaylistChangesBtn');
        const originalText = saveBtn.textContent;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Guardando...';
        
        // Enviar petición a la API
        const response = await fetch(`${API_URL}/playlists/${playlistId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(playlistData),
        });
        
        console.log('Respuesta del servidor:', response.status, response.statusText);
        
        if (!response.ok) {
            let errorMessage = `Error ${response.status}: ${response.statusText}`;
            
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
                console.error('Error detallado:', errorData);
            } catch (e) {
                console.error('Error al parsear respuesta de error:', e);
            }
            
            throw new Error(errorMessage);
        }
        
        const updatedPlaylist = await response.json();
        console.log("Playlist actualizada exitosamente:", updatedPlaylist);
        
        // Restaurar botón
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
        
        // Mostrar mensaje de éxito
        showToast('Lista de reproducción actualizada correctamente', 'success');
        
        // Cerrar el modal de edición
        const editModal = document.getElementById('editPlaylistModal');
        if (editModal && window.bootstrap) {
            try {
                const editModalInstance = bootstrap.Modal.getInstance(editModal);
                if (editModalInstance) {
                    editModalInstance.hide();
                    console.log('Modal de edición cerrado');
                }
            } catch (e) {
                console.error("Error al cerrar modal de edición:", e);
            }
        }
        
        // Recargar datos
        setTimeout(() => {
            try {
                console.log('Recargando datos...');
                if (typeof window.loadPlaylists === 'function') {
                    window.loadPlaylists();
                }
                
                // Si hay un currentPlaylistId, reabrir los detalles
                if (window.currentPlaylistId || currentPlaylistId) {
                    const id = window.currentPlaylistId || currentPlaylistId;
                    setTimeout(() => {
                        if (typeof window.openPlaylistDetail === 'function') {
                            window.openPlaylistDetail(id);
                        }
                    }, 1000);
                }
            } catch (error) {
                console.error("Error al recargar datos:", error);
            }
        }, 500);
        
        console.log('=== CAMBIOS GUARDADOS EXITOSAMENTE ===');
        
    } catch (error) {
        console.error('=== ERROR AL GUARDAR CAMBIOS ===', error);
        
        // Restaurar botón en caso de error
        const saveBtn = document.getElementById('savePlaylistChangesBtn');
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Guardar Cambios';
        }
        
        showToast(`Error al guardar cambios: ${error.message}`, 'error');
    }
};

async function deletePlaylist(playlistId) {
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al eliminar la lista');
        }
        
        showToast('Lista de reproducción eliminada correctamente', 'success');
        
        // Cerrar el modal de detalles de manera segura
        if (window.bootstrap) {
            try {
                const modal = document.getElementById('playlistDetailModal');
                if (modal) {
                    const modalInstance = bootstrap.Modal.getInstance(modal);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                }
            } catch (e) {
                console.error("Error al cerrar modal:", e);
            }
        }
        
        // Recargar playlists
        setTimeout(() => {
            loadPlaylists();
        }, 500);
        
    } catch (error) {
        console.error('Error al eliminar playlist:', error);
        showToast(`Error al eliminar la lista de reproducción: ${error.message}`, 'error');
    }
}

// ===== CONFIGURACIÓN DE EVENT LISTENERS =====

function setupVideoEventListeners() {
    console.log('Configurando event listeners de videos...');
    
    // Búsqueda de videos
    const videoSearchInput = document.getElementById('videoSearchInput');
    if (videoSearchInput) {
        videoSearchInput.removeEventListener('input', handleVideoSearch);
        videoSearchInput.addEventListener('input', handleVideoSearch);
    }

    // Limpiar búsqueda
    const clearVideoSearch = document.getElementById('clearVideoSearch');
    if (clearVideoSearch) {
        clearVideoSearch.removeEventListener('click', handleClearVideoSearch);
        clearVideoSearch.addEventListener('click', handleClearVideoSearch);
    }

    // Filtro de estado
    const videoFilterExpiration = document.getElementById('videoFilterExpiration');
    if (videoFilterExpiration) {
        videoFilterExpiration.removeEventListener('change', handleVideoFilter);
        videoFilterExpiration.addEventListener('change', handleVideoFilter);
    }

    // Selector de tamaño de página
    const videoPageSizeSelect = document.getElementById('videoPageSizeSelect');
    if (videoPageSizeSelect) {
        videoPageSizeSelect.removeEventListener('change', handlePageSizeChange);
        videoPageSizeSelect.addEventListener('change', handlePageSizeChange);
    }
}

function handleVideoSearch() {
    videoPagination.searchTerm = this.value.toLowerCase().trim();
    videoPagination.currentPage = 1;
    applyFiltersAndDisplayPage();
}

function handleClearVideoSearch() {
    const searchInput = document.getElementById('videoSearchInput');
    if (searchInput) {
        searchInput.value = '';
        videoPagination.searchTerm = '';
        videoPagination.currentPage = 1;
        applyFiltersAndDisplayPage();
    }
}

function handleVideoFilter() {
    videoPagination.filter = this.value;
    videoPagination.currentPage = 1;
    applyFiltersAndDisplayPage();
}

function handlePageSizeChange() {
    videoPagination.pageSize = parseInt(this.value);
    videoPagination.currentPage = 1;
    applyFiltersAndDisplayPage();
}

// ===== FUNCIONES DE PRUEBA DE CONEXIÓN =====

async function testApiConnection() {
    try {
        console.log("Probando conexión a API:", `${API_URL}/videos/`);
        const response = await fetch(`${API_URL}/videos/`);
        
        if (!response.ok) {
            console.error("La API no responde correctamente:", response.status, response.statusText);
            const errorMessage = document.createElement('div');
            errorMessage.className = 'alert alert-danger alert-dismissible fade show mt-3';
            errorMessage.innerHTML = `
                <strong>Error de conexión</strong>
                <p>No se puede conectar a la API: ${response.status} ${response.statusText}</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            document.body.prepend(errorMessage);
        } else {
            console.log("Conexión a API exitosa");
        }
    } catch (error) {
        console.error("Error al probar conexión:", error);
        const errorMessage = document.createElement('div');
        errorMessage.className = 'alert alert-danger alert-dismissible fade show mt-3';
        errorMessage.innerHTML = `
            <strong>Error de conexión</strong>
            <p>No se puede conectar a la API: ${error.message}</p>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.prepend(errorMessage);
    }
}

// ===== INICIALIZACIÓN =====

document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando aplicación...');
    
    // Probar conexión a la API
    try {
        testApiConnection();
    } catch (e) {
        console.error("Error al probar conexión:", e);
    }
    
    // Cargar datos iniciales según la pestaña activa
    try {
        const activeTab = document.querySelector('.nav-link.active');
        if (activeTab) {
            const target = activeTab.getAttribute('data-bs-target') || activeTab.getAttribute('href');
            if (target === '#videos') {
                loadVideos();
                setTimeout(setupVideoEventListeners, 500);
            } else if (target === '#playlists') {
                loadPlaylists();
            }
        }
    } catch (e) {
        console.error("Error al cargar datos iniciales:", e);
    }
    
    // Configurar event listeners para navegación por pestañas
    try {
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(e) {
                const target = e.target.getAttribute('data-bs-target') || e.target.getAttribute('href');
                if (target === '#videos') {
                    loadVideos();
                    setTimeout(setupVideoEventListeners, 500);
                } else if (target === '#playlists') {
                    loadPlaylists();
                }
            });
        });
    } catch (e) {
        console.error("Error al configurar navegación por pestañas:", e);
    }
    
    // Configurar filtros y búsquedas de playlists
    try {
        safeElementOperation('playlistFilterStatus', element => {
            element.addEventListener('change', function() {
                loadPlaylists(this.value);
            });
        });
        
        safeElementOperation('playlistSearchInput', element => {
            element.addEventListener('input', function() {
                if (this.value.length > 2 || this.value.length === 0) {
                    filterPlaylistsByTitle(this.value);
                }
            });
        });
        
        safeElementOperation('clearPlaylistSearch', element => {
            element.addEventListener('click', function() {
                const searchInput = document.getElementById('playlistSearchInput');
                if (searchInput) {
                    searchInput.value = '';
                }
                const filterSelect = document.getElementById('playlistFilterStatus');
                loadPlaylists(filterSelect ? filterSelect.value : 'all');
            });
        });
    } catch (e) {
        console.error("Error al configurar filtros y búsquedas:", e);
    }
    
    // Configurar formularios
    try {
        safeElementOperation('videoUploadForm', element => {
            element.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                
                const expirationInput = document.getElementById('videoExpiration');
                if (expirationInput && expirationInput.value) {
                    formData.append('expiration_date', expirationInput.value);
                }
                
                uploadVideo(formData);
            });
        });
        
        safeElementOperation('playlistCreateForm', element => {
            element.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const playlistData = {
                    title: document.getElementById('playlistTitle')?.value || '',
                    description: document.getElementById('playlistDescription')?.value || null,
                    start_date: document.getElementById('playlistStartDate')?.value || null,
                    expiration_date: document.getElementById('playlistExpiration')?.value || null,
                    is_active: document.getElementById('playlistActive')?.checked || false
                };
                
                createPlaylist(playlistData);
            });
        });
    } catch (e) {
        console.error("Error al configurar formularios:", e);
    }
    
    // Configurar botones de guardado
    try {
        safeElementOperation('saveVideoChangesBtn', element => {
            element.addEventListener('click', saveVideoChanges);
        });
        
        safeElementOperation('savePlaylistChangesBtn', element => {
            element.addEventListener('click', savePlaylistChanges);
        });
    } catch (e) {
        console.error("Error al configurar botones de guardado:", e);
    }
    
    console.log('Aplicación inicializada correctamente');
});

// ===== FUNCIONES DE DIAGNÓSTICO =====

window.debugVideoPagination = function() {
    console.log('=== DIAGNÓSTICO DE PAGINACIÓN DE VIDEOS ===');
    console.log('videoPagination:', videoPagination);
    console.log('allVideos.length:', allVideos.length);
    console.log('videosList element:', document.getElementById('videosList'));
    console.log('Funciones de navegación:');
    console.log('- goToFirstVideoPage:', typeof window.goToFirstVideoPage);
    console.log('- goToPrevVideoPage:', typeof window.goToPrevVideoPage);
    console.log('- goToNextVideoPage:', typeof window.goToNextVideoPage);
    console.log('- goToLastVideoPage:', typeof window.goToLastVideoPage);
    console.log('- goToVideoPage:', typeof window.goToVideoPage);
    console.log('- sortVideoTable:', typeof window.sortVideoTable);
    console.log('=== FIN DIAGNÓSTICO ===');
};

// ===== EXPONER FUNCIONES GLOBALMENTE =====

// Asegurar que las funciones estén disponibles globalmente
window.openPlaylistDetail = window.openPlaylistDetail;
window.removeVideoFromPlaylist = window.removeVideoFromPlaylist;
window.removeDeviceFromPlaylist = window.removeDeviceFromPlaylist;
window.loadVideos = window.loadVideos;
window.loadPlaylists = loadPlaylists;
window.editVideo = editVideo;
window.deleteVideo = deleteVideo;
window.saveVideoChanges = saveVideoChanges;
window.savePlaylistChanges = savePlaylistChanges;
window.createPlaylist = createPlaylist;

console.log('main.js cargado completamente - Todas las funciones disponibles');