// Variables globales para paginación de playlists
let currentPlaylistPage = 1;
let playlistPageSize = 100;
let totalPlaylistItems = 0;
let totalPlaylistPages = 1;
let allPlaylists = [];
let filteredPlaylists = [];
let currentPlaylistFilter = 'all';
let currentPlaylistSearchTerm = '';
let playlistSortField = '';
let playlistSortDirection = 'asc';

// Función debounce para optimizar la búsqueda
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Funciones auxiliares
function isPlaylistActive(playlist) {
    if (!playlist.is_active) return false;
    if (!playlist.expiration_date) return true;
    return new Date(playlist.expiration_date) > new Date();
}

function isExpired(dateString) {
    return new Date(dateString) < new Date();
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('es-ES', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showPlaylistLoading(show) {
    const playlistsList = document.getElementById('playlistsList');
    if (!playlistsList) return;
    
    if (show) {
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
    }
}

function showPlaylistError(message) {
    const playlistsList = document.getElementById('playlistsList');
    if (!playlistsList) return;
    
    playlistsList.innerHTML = `
        <tr>
            <td colspan="6" class="text-center py-5">
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    ${message}
                </div>
            </td>
        </tr>
    `;
}

function sortPlaylists(playlists, field, direction) {
    return [...playlists].sort((a, b) => {
        let aVal, bVal;
        
        switch (field) {
            case 'title':
                aVal = (a.title || '').toLowerCase();
                bVal = (b.title || '').toLowerCase();
                break;
            case 'video_count':
                aVal = a.videos ? a.videos.length : 0;
                bVal = b.videos ? b.videos.length : 0;
                break;
            case 'expiration_date':
                aVal = a.expiration_date ? new Date(a.expiration_date) : new Date(0);
                bVal = b.expiration_date ? new Date(b.expiration_date) : new Date(0);
                break;
            case 'created_at':
                aVal = a.created_at ? new Date(a.created_at) : new Date(0);
                bVal = b.created_at ? new Date(b.created_at) : new Date(0);
                break;
            default:
                return 0;
        }
        
        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });
}

// Función principal para cargar playlists con paginación
async function loadPlaylists(filter = 'all') {
    console.log("Cargando playlists con filtro:", filter);
    
    const playlistsList = document.getElementById('playlistsList');
    if (!playlistsList) {
        console.error("Elemento playlistsList no encontrado");
        return;
    }
    
    try {
        // Mostrar indicador de carga
        showPlaylistLoading(true);
        
        // Cargar TODAS las playlists (sin límite de 100)
        const response = await fetch(`${API_URL}/playlists/?limit=10000`);
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }
        
        allPlaylists = await response.json();
        console.log(`Cargadas ${allPlaylists.length} listas de reproducción`);
        
        if (!Array.isArray(allPlaylists)) {
            console.error("Datos recibidos no son un array:", allPlaylists);
            throw new Error("Formato de datos inválido");
        }
        
        currentPlaylistFilter = filter;
        currentPlaylistPage = 1;
        
        applyPlaylistFiltersAndSearch();
        
    } catch (error) {
        console.error('Error al cargar playlists:', error);
        showPlaylistError('Error al cargar listas de reproducción: ' + error.message);
    } finally {
        showPlaylistLoading(false);
    }
}

// Aplicar filtros y búsqueda de playlists
function applyPlaylistFiltersAndSearch() {
    let filtered = allPlaylists;
    
    // Filtrar por estado
    if (currentPlaylistFilter === 'active') {
        filtered = allPlaylists.filter(playlist => isPlaylistActive(playlist));
    } else if (currentPlaylistFilter === 'inactive') {
        filtered = allPlaylists.filter(playlist => !isPlaylistActive(playlist));
    }

    // Filtrar por búsqueda
    if (currentPlaylistSearchTerm) {
        filtered = filtered.filter(playlist => 
            (playlist.title || '').toLowerCase().includes(currentPlaylistSearchTerm) ||
            (playlist.description || '').toLowerCase().includes(currentPlaylistSearchTerm)
        );
    }

    // Aplicar ordenamiento si está configurado
    if (playlistSortField) {
        filtered = sortPlaylists(filtered, playlistSortField, playlistSortDirection);
    }

    filteredPlaylists = filtered;
    totalPlaylistItems = filtered.length;
    totalPlaylistPages = Math.ceil(totalPlaylistItems / playlistPageSize);
    
    // Ajustar página actual si es necesario
    if (currentPlaylistPage > totalPlaylistPages && totalPlaylistPages > 0) {
        currentPlaylistPage = totalPlaylistPages;
    }
    if (currentPlaylistPage < 1) {
        currentPlaylistPage = 1;
    }

    updatePlaylistPaginationInfo();
    displayCurrentPlaylistPage();
    updatePlaylistPaginationButtons();
}

// Mostrar página actual de playlists
function displayCurrentPlaylistPage() {
    const startIndex = (currentPlaylistPage - 1) * playlistPageSize;
    const endIndex = Math.min(startIndex + playlistPageSize, totalPlaylistItems);
    const pageData = filteredPlaylists.slice(startIndex, endIndex);

    const playlistsList = document.getElementById('playlistsList');
    
    if (pageData.length === 0) {
        playlistsList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5">
                    <div class="text-muted">
                        <i class="fas fa-search fa-3x mb-3"></i>
                        <p class="mb-0">No se encontraron listas de reproducción</p>
                        ${currentPlaylistSearchTerm ? '<p class="small">Intenta con otros términos de búsqueda</p>' : ''}
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    const rows = pageData.map(playlist => {
        const active = isPlaylistActive(playlist);
        const expirationText = playlist.expiration_date 
            ? `${isExpired(playlist.expiration_date) ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`
            : 'Sin expiración';

        return `
            <tr class="${active ? '' : 'table-warning'}">
                <td>
                    <strong>${escapeHtml(playlist.title || 'Sin título')}</strong>
                </td>
                <td>
                    <span class="text-muted">${escapeHtml(playlist.description || 'Sin descripción')}</span>
                </td>
                <td>
                    <span class="badge bg-info">${playlist.videos ? playlist.videos.length : 0} videos</span>
                </td>
                <td>
                    <small class="text-muted">${expirationText}</small>
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
    }).join('');

    playlistsList.innerHTML = rows;
}

// Actualizar información de paginación
function updatePlaylistPaginationInfo() {
    const startItem = totalPlaylistItems > 0 ? (currentPlaylistPage - 1) * playlistPageSize + 1 : 0;
    const endItem = Math.min(currentPlaylistPage * playlistPageSize, totalPlaylistItems);
    
    const playlistCountBadge = document.getElementById('playlistCountBadge');
    if (playlistCountBadge) {
        playlistCountBadge.textContent = `${totalPlaylistItems} listas`;
    }
    
    const paginationInfo = document.getElementById('playlistPaginationInfo');
    if (paginationInfo) {
        paginationInfo.textContent = `Mostrando ${startItem} - ${endItem} de ${totalPlaylistItems} resultados`;
    }
}

// Función actualizada para manejar los botones de paginación
function updatePlaylistPaginationButtons() {
    const firstBtn = document.getElementById('firstPlaylistPageBtn');
    const prevBtn = document.getElementById('prevPlaylistPageBtn');
    const nextBtn = document.getElementById('nextPlaylistPageBtn');
    const lastBtn = document.getElementById('lastPlaylistPageBtn');
    const pageInput = document.getElementById('playlistPageInput');
    const totalPagesSpan = document.getElementById('totalPlaylistPages');
    const paginationFooter = document.getElementById('playlistPaginationFooter');
    
    if (firstBtn) firstBtn.disabled = currentPlaylistPage <= 1;
    if (prevBtn) prevBtn.disabled = currentPlaylistPage <= 1;
    if (nextBtn) nextBtn.disabled = currentPlaylistPage >= totalPlaylistPages;
    if (lastBtn) lastBtn.disabled = currentPlaylistPage >= totalPlaylistPages;
    
    if (pageInput) {
        pageInput.value = currentPlaylistPage;
        pageInput.max = totalPlaylistPages;
    }
    
    if (totalPagesSpan) {
        totalPagesSpan.textContent = totalPlaylistPages;
    }
    
    if (paginationFooter) {
        const startItem = totalPlaylistItems > 0 ? (currentPlaylistPage - 1) * playlistPageSize + 1 : 0;
        const endItem = Math.min(currentPlaylistPage * playlistPageSize, totalPlaylistItems);
        paginationFooter.innerHTML = `
            Página ${currentPlaylistPage} de ${totalPlaylistPages} 
            <span class="text-primary">(${startItem}-${endItem} de ${totalPlaylistItems})</span>
        `;
    }
}

// Ir a una página específica de playlists
function goToPlaylistPage(page) {
    if (page >= 1 && page <= totalPlaylistPages && page !== currentPlaylistPage) {
        currentPlaylistPage = page;
        displayCurrentPlaylistPage();
        updatePlaylistPaginationInfo();
        updatePlaylistPaginationButtons();
        
        // Scroll al top de la tabla
        const tableContainer = document.getElementById('playlistsTable');
        if (tableContainer) {
            tableContainer.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
        }
    }
}

// Buscar playlists
function searchPlaylists() {
    const searchInput = document.getElementById('playlistSearchInput');
    if (searchInput) {
        currentPlaylistSearchTerm = searchInput.value.toLowerCase().trim();
        currentPlaylistPage = 1;
        applyPlaylistFiltersAndSearch();
    }
}

// Limpiar búsqueda de playlists
function clearPlaylistSearch() {
    const searchInput = document.getElementById('playlistSearchInput');
    if (searchInput) {
        searchInput.value = '';
        currentPlaylistSearchTerm = '';
        currentPlaylistPage = 1;
        applyPlaylistFiltersAndSearch();
    }
}

// Cambiar tamaño de página
function changePlaylistPageSize(newSize) {
    playlistPageSize = parseInt(newSize);
    currentPlaylistPage = 1;
    applyPlaylistFiltersAndSearch();
}

// Funciones adicionales para navegación de páginas (para usar en botones HTML)
function goToFirstPlaylistPage() {
    goToPlaylistPage(1);
}

function goToPrevPlaylistPage() {
    if (currentPlaylistPage > 1) {
        goToPlaylistPage(currentPlaylistPage - 1);
    }
}

function goToNextPlaylistPage() {
    if (currentPlaylistPage < totalPlaylistPages) {
        goToPlaylistPage(currentPlaylistPage + 1);
    }
}

function goToLastPlaylistPage() {
    goToPlaylistPage(totalPlaylistPages);
}

// Función para ordenar tabla por columna
function sortPlaylistTable(field) {
    if (playlistSortField === field) {
        playlistSortDirection = playlistSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        playlistSortField = field;
        playlistSortDirection = 'asc';
    }
    
    applyPlaylistFiltersAndSearch();
    
    // Actualizar iconos de ordenamiento
    document.querySelectorAll('#playlistsTable th .fas.fa-sort, #playlistsTable th .fas.fa-sort-up, #playlistsTable th .fas.fa-sort-down')
        .forEach(icon => {
            icon.className = 'fas fa-sort';
        });
    
    const activeIcon = document.querySelector(`#playlistsTable th button[onclick="sortPlaylistTable('${field}')"] i`);
    if (activeIcon) {
        activeIcon.className = `fas fa-sort-${playlistSortDirection === 'asc' ? 'up' : 'down'}`;
    }
}

// Event listeners para paginación de playlists
document.addEventListener('DOMContentLoaded', function() {
    console.log('Inicializando event listeners para paginación de playlists...');
    
    // Filtro de estado de playlists
    const playlistFilterStatus = document.getElementById('playlistFilterStatus');
    if (playlistFilterStatus) {
        console.log('Configurando filtro de estado de playlists');
        playlistFilterStatus.addEventListener('change', function() {
            console.log('Cambio de filtro:', this.value);
            currentPlaylistFilter = this.value;
            currentPlaylistPage = 1;
            applyPlaylistFiltersAndSearch();
        });
    }

    // Búsqueda de playlists con debounce
    const playlistSearchInput = document.getElementById('playlistSearchInput');
    if (playlistSearchInput) {
        console.log('Configurando búsqueda de playlists');
        playlistSearchInput.addEventListener('input', debounce(function() {
            console.log('Búsqueda:', this.value);
            searchPlaylists();
        }, 300));
    }

    // Limpiar búsqueda de playlists
    const clearPlaylistSearchBtn = document.getElementById('clearPlaylistSearch');
    if (clearPlaylistSearchBtn) {
        console.log('Configurando botón limpiar búsqueda');
        clearPlaylistSearchBtn.addEventListener('click', function() {
            console.log('Limpiando búsqueda');
            clearPlaylistSearch();
        });
    }

    // Selector de tamaño de página
    const playlistPageSizeSelect = document.getElementById('playlistPageSizeSelect');
    if (playlistPageSizeSelect) {
        console.log('Configurando selector de tamaño de página');
        playlistPageSizeSelect.addEventListener('change', function() {
            console.log('Cambio de tamaño de página:', this.value);
            changePlaylistPageSize(this.value);
        });
    }

    // Configurar navegación por pestañas para cargar playlists
    const playlistTab = document.getElementById('playlists-tab');
    if (playlistTab) {
        console.log('Configurando pestaña de playlists');
        playlistTab.addEventListener('shown.bs.tab', function(e) {
            console.log('Pestaña de playlists activada');
            loadPlaylists(currentPlaylistFilter);
        });
    }

    console.log('Event listeners para paginación de playlists configurados');
});

// Sobrescribir la función original para usar la nueva funcionalidad
window.loadPlaylists = loadPlaylists;

console.log('Módulo de paginación de playlists cargado correctamente');