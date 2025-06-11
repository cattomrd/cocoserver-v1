// ==================================================
// SISTEMA DE PAGINACIÓN PARA BIBLIOTECA DE VIDEOS
// ==================================================
// Agregar este código al final de videos.html o en un archivo separado
// similar a como está implementado playlist_pagination.html

(function() {
    console.log('Inicializando sistema de paginación para videos...');
    
    // Variables globales para paginación de videos
    let allVideos = [];
    let videoPagination = {
        currentPage: 1,
        pageSize: 100,
        totalItems: 0,
        totalPages: 1,
        filteredData: [],
        searchTerm: '',
        filter: 'all',
        sortField: 'title',
        sortOrder: 'asc'
    };

    // ===== FUNCIONES HELPER =====
    function isVideoExpiredPagination(expirationDate) {
        if (!expirationDate) return false;
        return new Date(expirationDate) < new Date();
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

    // ===== FUNCIONES DE PAGINACIÓN =====

    // Aplicar filtros y mostrar página actual
    function applyFiltersAndDisplayPage() {
        console.log('Aplicando filtros de videos y mostrando página');
        
        let filtered = [...allVideos];

        // Filtrar por estado de expiración
        if (videoPagination.filter === 'active') {
            filtered = filtered.filter(video => !isVideoExpiredPagination(video.expiration_date));
        } else if (videoPagination.filter === 'expired') {
            filtered = filtered.filter(video => isVideoExpiredPagination(video.expiration_date));
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

        displayCurrentPage();
        updatePaginationInfo();
        updatePaginationButtons();
    }

    // Mostrar página actual
    function displayCurrentPage() {
        const startIndex = (videoPagination.currentPage - 1) * videoPagination.pageSize;
        const endIndex = Math.min(startIndex + videoPagination.pageSize, videoPagination.totalItems);
        const pageData = videoPagination.filteredData.slice(startIndex, endIndex);

        const videosList = document.getElementById('videosList');
        if (!videosList) return;
        
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
            const isExpired = isVideoExpiredPagination(video.expiration_date);
            const expirationText = video.expiration_date 
                ? `${isExpired ? 'Expiró' : 'Expira'}: ${formatDatePagination(video.expiration_date)}`
                : 'Sin expiración';

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
                            `<span class="badge ${isExpired ? 'bg-danger' : 'bg-info'}">${expirationText}</span>` : 
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
    }

    // Actualizar información de paginación
    function updatePaginationInfo() {
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
    }

    // Actualizar botones de paginación
    function updatePaginationButtons() {
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
    }

    // ===== FUNCIONES PÚBLICAS DE NAVEGACIÓN =====
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

    // Función de ordenamiento
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

    // ===== FUNCIÓN PRINCIPAL DE CARGA =====
    async function loadVideos(filter = 'all') {
        console.log("Cargando videos con paginación, filtro:", filter);
        
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
            
            // Cargar TODOS los videos (sin límite)
            const response = await fetch(`${API_URL}/videos/?limit=10000`);
            
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
            }
            
            const responseData = await response.json();
            allVideos = Array.isArray(responseData) ? responseData : responseData.items || [];
            
            console.log(`Cargados ${allVideos.length} videos`);
            
            if (!Array.isArray(allVideos)) {
                console.error("Datos recibidos no son un array:", allVideos);
                throw new Error("Formato de datos incorrecto");
            }
            
            // Aplicar filtro inicial
            videoPagination.filter = filter;
            videoPagination.currentPage = 1;
            applyFiltersAndDisplayPage();
            
        } catch (error) {
            console.error('Error al cargar videos:', error);
            videosList.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div class="alert alert-danger mb-0">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Error al cargar videos: ${error.message}
                        </div>
                    </td>
                </tr>
            `;
        }
    }

    // ===== INTERCEPTAR FUNCIÓN ORIGINAL =====
    function interceptVideoLoading() {
        // Guardar la función original si existe
        const originalLoadVideos = window.loadVideos;
        
        // Crear nueva función que reemplace la original
        window.loadVideos = async function(filter = 'all', searchTerm = '') {
            console.log('loadVideos interceptado para paginación');
            
            // Llamar a nuestra función con paginación
            await loadVideos(filter);
            
            // Si había un término de búsqueda, aplicarlo
            if (searchTerm) {
                const videoSearchInput = document.getElementById('videoSearchInput');
                if (videoSearchInput) {
                    videoSearchInput.value = searchTerm;
                    videoPagination.searchTerm = searchTerm.toLowerCase().trim();
                    videoPagination.currentPage = 1;
                    applyFiltersAndDisplayPage();
                }
            }
        };
    }

    // ===== EVENT LISTENERS =====
    function setupEventListeners() {
        // Búsqueda de videos
        const videoSearchInput = document.getElementById('videoSearchInput');
        if (videoSearchInput) {
            videoSearchInput.addEventListener('input', function() {
                videoPagination.searchTerm = this.value.toLowerCase().trim();
                videoPagination.currentPage = 1;
                applyFiltersAndDisplayPage();
            });
        }

        // Limpiar búsqueda
        const clearVideoSearch = document.getElementById('clearVideoSearch');
        if (clearVideoSearch) {
            clearVideoSearch.addEventListener('click', function() {
                const searchInput = document.getElementById('videoSearchInput');
                if (searchInput) {
                    searchInput.value = '';
                    videoPagination.searchTerm = '';
                    videoPagination.currentPage = 1;
                    applyFiltersAndDisplayPage();
                }
            });
        }

        // Filtro de estado de expiración
        const videoFilterExpiration = document.getElementById('videoFilterExpiration');
        if (videoFilterExpiration) {
            videoFilterExpiration.addEventListener('change', function() {
                videoPagination.filter = this.value;
                videoPagination.currentPage = 1;
                applyFiltersAndDisplayPage();
            });
        }

        // Selector de tamaño de página
        const videoPageSizeSelect = document.getElementById('videoPageSizeSelect');
        if (videoPageSizeSelect) {
            videoPageSizeSelect.addEventListener('change', function() {
                videoPagination.pageSize = parseInt(this.value);
                videoPagination.currentPage = 1;
                applyFiltersAndDisplayPage();
            });
        }

        console.log('Event listeners de paginación de videos configurados');
    }

    // ===== INICIALIZACIÓN =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                interceptVideoLoading();
                setupEventListeners();
                console.log('Paginación de videos inicializada');
            }, 500);
        });
    } else {
        setTimeout(() => {
            interceptVideoLoading();
            setupEventListeners();
            console.log('Paginación de videos inicializada');
        }, 500);
    }
})();