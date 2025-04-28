// Función para realizar la búsqueda de videos
function searchVideos() {
    const searchInput = document.getElementById('videoSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    const videoRows = document.querySelectorAll('#videosList tr');
    let visibleCount = 0;
    
    videoRows.forEach(row => {
        // Ignorar la fila de carga si existe
        if (row.id === 'videosLoading') return;
        
        // Obtener el título del video (primera columna)
        const title = row.cells[0]?.textContent.toLowerCase() || '';
        // También buscar en la descripción (segunda columna)
        const description = row.cells[1]?.textContent.toLowerCase() || '';
        
        // Verificar si coincide con el término de búsqueda
        if (title.includes(searchTerm) || description.includes(searchTerm)) {
            row.style.display = ''; // Mostrar la fila
            visibleCount++;
        } else {
            row.style.display = 'none'; // Ocultar la fila
        }
    });
    
    // Actualizar contador de videos
    const countBadge = document.getElementById('videoCountBadge');
    if (countBadge) {
        countBadge.textContent = `${visibleCount} video${visibleCount !== 1 ? 's' : ''}`;
    }
    
    // Mostrar mensaje si no hay resultados
    const noResultsRow = document.getElementById('noVideoResults');
    if (visibleCount === 0) {
        if (!noResultsRow) {
            const tbody = document.getElementById('videosList');
            const newRow = document.createElement('tr');
            newRow.id = 'noVideoResults';
            newRow.innerHTML = `
                <td colspan="7" class="text-center py-4">
                    <div class="alert alert-info mb-0">
                        No se encontraron videos que coincidan con "${searchTerm}"
                    </div>
                </td>
            `;
            tbody.appendChild(newRow);
        } else {
            noResultsRow.style.display = '';
            const alertDiv = noResultsRow.querySelector('.alert');
            if (alertDiv) {
                alertDiv.textContent = `No se encontraron videos que coincidan con "${searchTerm}"`;
            }
        }
    } else if (noResultsRow) {
        noResultsRow.style.display = 'none';
    }
}

// Configurar los event listeners cuando se carga el documento
document.addEventListener('DOMContentLoaded', function() {
    // Event listener existente (no tocar)...
    
    // Agregar event listener para la búsqueda de videos
    const videoSearchInput = document.getElementById('videoSearchInput');
    if (videoSearchInput) {
        videoSearchInput.addEventListener('input', searchVideos);
    }
    
    // Agregar event listener para limpiar la búsqueda
    const clearVideoSearch = document.getElementById('clearVideoSearch');
    if (clearVideoSearch) {
        clearVideoSearch.addEventListener('click', function() {
            const searchInput = document.getElementById('videoSearchInput');
            if (searchInput) {
                searchInput.value = '';
                searchVideos(); // Actualizar la vista
            }
        });
    }
    
    // Actualizar el contador inicial de videos
    const updateVideoCount = function() {
        const countBadge = document.getElementById('videoCountBadge');
        const videoRows = document.querySelectorAll('#videosList tr:not(#videosLoading):not([style*="display: none"])');
        if (countBadge) {
            const count = videoRows.length;
            countBadge.textContent = `${count} video${count !== 1 ? 's' : ''}`;
        }
    };
    
    // Observar cambios en la tabla de videos para actualizar el contador
    const videosList = document.getElementById('videosList');
    if (videosList) {
        const observer = new MutationObserver(updateVideoCount);
        observer.observe(videosList, { childList: true, subtree: true, attributes: true });
        
        // También actualizar cuando se cambie de pestaña
        document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(e) {
                if (e.target.getAttribute('href') === '#videos') {
                    updateVideoCount();
                }
            });
        });
        
        // Actualizar después de cargar la página
        setTimeout(updateVideoCount, 1000);
    }
});

// Sobreescribir la función loadVideos para mantener la búsqueda al recargar
const originalLoadVideos = window.loadVideos;
window.loadVideos = async function(filter = 'all', searchTerm = '') {
    await originalLoadVideos(filter, searchTerm);
    
    // Aplicar filtro de búsqueda actual después de cargar
    const videoSearchInput = document.getElementById('videoSearchInput');
    if (videoSearchInput && videoSearchInput.value.trim()) {
        searchVideos();
    }
};

// Función para realizar la búsqueda de listas de reproducción
function searchPlaylists() {
    const searchInput = document.getElementById('playlistSearchInput');
    const searchTerm = searchInput.value.toLowerCase().trim();
    const playlistRows = document.querySelectorAll('#playlistsList tr');
    let visibleCount = 0;
    
    playlistRows.forEach(row => {
        // Ignorar la fila de carga si existe
        if (row.id === 'playlistsLoading') return;
        
        // Obtener el título de la playlist (primera columna)
        const title = row.cells[0]?.textContent.toLowerCase() || '';
        // También buscar en la descripción (segunda columna)
        const description = row.cells[1]?.textContent.toLowerCase() || '';
        
        // Verificar si coincide con el término de búsqueda
        if (title.includes(searchTerm) || description.includes(searchTerm)) {
            row.style.display = ''; // Mostrar la fila
            visibleCount++;
        } else {
            row.style.display = 'none'; // Ocultar la fila
        }
    });
    
    // Actualizar contador de playlists
    const countBadge = document.getElementById('playlistCountBadge');
    if (countBadge) {
        countBadge.textContent = `${visibleCount} lista${visibleCount !== 1 ? 's' : ''}`;
    }
    
    // Mostrar mensaje si no hay resultados
    const noResultsRow = document.getElementById('noPlaylistResults');
    if (visibleCount === 0) {
        if (!noResultsRow) {
            const tbody = document.getElementById('playlistsList');
            const newRow = document.createElement('tr');
            newRow.id = 'noPlaylistResults';
            newRow.innerHTML = `
                <td colspan="6" class="text-center py-4">
                    <div class="alert alert-info mb-0">
                        No se encontraron listas que coincidan con "${searchTerm}"
                    </div>
                </td>
            `;
            tbody.appendChild(newRow);
        } else {
            noResultsRow.style.display = '';
            const alertDiv = noResultsRow.querySelector('.alert');
            if (alertDiv) {
                alertDiv.textContent = `No se encontraron listas que coincidan con "${searchTerm}"`;
            }
        }
    } else if (noResultsRow) {
        noResultsRow.style.display = 'none';
    }
}

// Ampliar la función DOMContentLoaded para incluir los listeners de playlist
document.addEventListener('DOMContentLoaded', function() {
    // Código existente para videos...
    
    // Agregar event listener para la búsqueda de playlists
    const playlistSearchInput = document.getElementById('playlistSearchInput');
    if (playlistSearchInput) {
        playlistSearchInput.addEventListener('input', searchPlaylists);
    }
    
    // Agregar event listener para limpiar la búsqueda de playlists
    const clearPlaylistSearch = document.getElementById('clearPlaylistSearch');
    if (clearPlaylistSearch) {
        clearPlaylistSearch.addEventListener('click', function() {
            const searchInput = document.getElementById('playlistSearchInput');
            if (searchInput) {
                searchInput.value = '';
                searchPlaylists(); // Actualizar la vista
            }
        });
    }
    
    // Actualizar el contador inicial de playlists
    const updatePlaylistCount = function() {
        const countBadge = document.getElementById('playlistCountBadge');
        const playlistRows = document.querySelectorAll('#playlistsList tr:not(#playlistsLoading):not([style*="display: none"])');
        if (countBadge) {
            const count = playlistRows.length;
            countBadge.textContent = `${count} lista${count !== 1 ? 's' : ''}`;
        }
    };
    
    // Observar cambios en la tabla de playlists para actualizar el contador
    const playlistsList = document.getElementById('playlistsList');
    if (playlistsList) {
        const observer = new MutationObserver(updatePlaylistCount);
        observer.observe(playlistsList, { childList: true, subtree: true, attributes: true });
        
        // También actualizar cuando se cambie de pestaña
        document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(e) {
                if (e.target.getAttribute('href') === '#playlists') {
                    updatePlaylistCount();
                }
            });
        });
        
        // Actualizar después de cargar la página
        setTimeout(updatePlaylistCount, 1000);
    }
});

// Sobreescribir la función loadPlaylists para mantener la búsqueda al recargar
const originalLoadPlaylists = window.loadPlaylists;
window.loadPlaylists = async function(filter = 'all') {
    await originalLoadPlaylists(filter);
    
    // Aplicar filtro de búsqueda actual después de cargar
    const playlistSearchInput = document.getElementById('playlistSearchInput');
    if (playlistSearchInput && playlistSearchInput.value.trim()) {
        searchPlaylists();
    }
};