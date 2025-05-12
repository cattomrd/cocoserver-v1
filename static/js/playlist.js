// Variables globales
let allPlaylists = [];
let currentPlaylistId = null;
const API_URL = window.API_URL || "/api"; // Asegurarse de que API_URL está definido

// Función auxiliar para verificar si una fecha ha expirado
function isExpired(dateString) {
    if (!dateString) return false;
    const expirationDate = new Date(dateString);
    const now = new Date();
    return expirationDate < now;
}

// Función auxiliar para formatear fechas
function formatDate(dateString) {
    if (!dateString) return 'Sin fecha';
    
    try {
        const date = new Date(dateString);
        // Verificar si la fecha es válida
        if (isNaN(date.getTime())) {
            return 'Fecha inválida';
        }
        return date.toLocaleString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch(e) {
        console.error("Error al formatear fecha:", e);
        return 'Error de formato';
    }
}

// Función para verificar si una playlist está activa
function isPlaylistActive(playlist) {
    if (!playlist) return false;
    if (playlist.is_active === false) return false;
    if (playlist.expiration_date && isExpired(playlist.expiration_date)) return false;
    return true;
}

// Mostrar notificación
function showToast(message, type = 'success') {
    console.log(`Notificación (${type}): ${message}`);
    
    // Verificar si existe algún sistema de notificaciones
    if (window.Toastify) {
        Toastify({
            text: message,
            duration: 3000,
            close: true,
            gravity: "top",
            position: "right",
            backgroundColor: type === 'success' ? "#4caf50" : "#f44336"
        }).showToast();
    } else if (window.bootstrap && typeof bootstrap.Toast !== 'undefined') {
        // Intentar usar Bootstrap Toast si está disponible
        try {
            // Crear un toast dinámicamente
            const toastContainer = document.querySelector('.toast-container');
            let container = toastContainer;
            
            // Si no existe un contenedor de toast, crearlo
            if (!container) {
                container = document.createElement('div');
                container.className = 'toast-container position-fixed top-0 end-0 p-3';
                document.body.appendChild(container);
            }
            
            // Crear el elemento toast
            const toastEl = document.createElement('div');
            toastEl.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0`;
            toastEl.setAttribute('role', 'alert');
            toastEl.setAttribute('aria-live', 'assertive');
            toastEl.setAttribute('aria-atomic', 'true');
            
            // Crear el contenido del toast
            toastEl.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            // Añadir el toast al contenedor
            container.appendChild(toastEl);
            
            // Inicializar y mostrar el toast
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
            
            // Eliminar el toast del DOM después de ocultarse
            toastEl.addEventListener('hidden.bs.toast', () => {
                toastEl.remove();
            });
        } catch (e) {
            console.error("Error al crear toast de Bootstrap:", e);
            alert(message);
        }
    } else {
        // Fallback a un alert básico si no hay sistema de toast
        alert(message);
    }
}

// Inicializar eventos cuando el DOM esté cargado
document.addEventListener('DOMContentLoaded', function() {
    console.log("Inicializando eventos para la gestión de playlists...");
    
    // Cargar playlists al iniciar
    try {
        loadPlaylists();
    } catch (e) {
        console.error("Error al cargar playlists inicialmente:", e);
    }
    
    // Cargar playlists activas para Raspberry Pi
    try {
        loadRaspberryActivePlaylists();
    } catch (e) {
        console.error("Error al cargar playlists para Raspberry Pi:", e);
    }
    
    // Event listeners para filtros
    const playlistFilterStatus = document.getElementById('playlistFilterStatus');
    if (playlistFilterStatus) {
        playlistFilterStatus.addEventListener('change', function() {
            try {
                loadPlaylists(this.value);
            } catch (e) {
                console.error("Error al filtrar playlists:", e);
            }
        });
    }
    
    // Event listener para búsqueda
    const playlistSearchInput = document.getElementById('playlistSearchInput');
    if (playlistSearchInput) {
        playlistSearchInput.addEventListener('input', function() {
            try {
                filterPlaylistsByTitle(this.value);
            } catch (e) {
                console.error("Error al buscar playlists:", e);
            }
        });
        
        // Limpiar búsqueda
        const clearSearchBtn = document.getElementById('clearPlaylistSearch');
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', function() {
                if (playlistSearchInput) {
                    playlistSearchInput.value = '';
                    try {
                        filterPlaylistsByTitle('');
                    } catch (e) {
                        console.error("Error al limpiar búsqueda:", e);
                    }
                }
            });
        }
    }
    
    // Event listener para formulario de creación de playlist
    const playlistCreateForm = document.getElementById('playlistCreateForm');
    if (playlistCreateForm) {
        playlistCreateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            try {
                createPlaylist();
            } catch (e) {
                console.error("Error al crear playlist:", e);
                showToast("Error al crear la lista de reproducción: " + e.message, "error");
            }
        });
    }
    
    // Event listener para botón de guardar cambios de playlist
    const savePlaylistChangesBtn = document.getElementById('savePlaylistChangesBtn');
    if (savePlaylistChangesBtn) {
        savePlaylistChangesBtn.addEventListener('click', function() {
            try {
                savePlaylistChanges();
            } catch (e) {
                console.error("Error al guardar cambios de playlist:", e);
                showToast("Error al guardar cambios: " + e.message, "error");
            }
        });
    }
    
    console.log("Inicialización de eventos para playlists completada");
});

// Función para cargar playlists
async function loadPlaylists(filter = 'all') {
    console.log("Cargando playlists con filtro:", filter);
    
    // Obtener contenedor
    const playlistsList = document.getElementById('playlistsList');
    if (!playlistsList) {
        console.error("Elemento playlistsList no encontrado");
        return;
    }
    
    try {
        // Mostrar indicador de carga
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
        
        // Realizar petición a la API
        const response = await fetch(`${API_URL}/playlists/`);
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }
        
        // Procesar respuesta
        allPlaylists = await response.json();
        console.log("Playlists cargadas:", allPlaylists);
        
        if (!Array.isArray(allPlaylists)) {
            console.error("Datos recibidos no son un array:", allPlaylists);
            throw new Error("Formato de datos inválido");
        }
        
        // Filtrar playlists según el criterio seleccionado
        let filteredPlaylists = allPlaylists;
        if (filter === 'active') {
            filteredPlaylists = allPlaylists.filter(playlist => isPlaylistActive(playlist));
        } else if (filter === 'inactive') {
            filteredPlaylists = allPlaylists.filter(playlist => !isPlaylistActive(playlist));
        }
        
        // Actualizar contador de playlists
        const playlistCountBadge = document.getElementById('playlistCountBadge');
        if (playlistCountBadge) {
            playlistCountBadge.textContent = `${filteredPlaylists.length} listas`;
        }
        
        // Mostrar el resultado según el modo de visualización actual
        const tableMode = playlistsList.closest('table') !== null;
        
        if (filteredPlaylists.length === 0) {
            if (tableMode) {
                playlistsList.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center py-5">
                            <p>No hay listas de reproducción disponibles. ¡Crea tu primera lista!</p>
                        </td>
                    </tr>
                `;
            } else {
                playlistsList.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <p>No hay listas de reproducción disponibles. ¡Crea tu primera lista!</p>
                    </div>
                `;
            }
            return;
        }
        
        // Limpiar contenedor
        playlistsList.innerHTML = '';
        
        // Mostrar playlists en formato tabla o tarjetas según corresponda
        if (tableMode) {
            // Modo tabla
            filteredPlaylists.forEach(playlist => {
                const active = isPlaylistActive(playlist);
                const expirationText = playlist.expiration_date 
                    ? `${isExpired(playlist.expiration_date) ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`
                    : 'Sin fecha de expiración';
                    
                const row = document.createElement('tr');
                row.className = active ? '' : 'table-danger';
                
                row.innerHTML = `
                    <td>${playlist.title}</td>
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
                        <button class="btn btn-primary" onclick="openPlaylistDetail(${playlist.id})">
                            <i class="fas fa-eye"></i> Ver Detalles
                        </button>
                    </td>
                `;
                playlistsList.appendChild(row);
            });
        } else {
            // Modo tarjetas
            filteredPlaylists.forEach(playlist => {
                const active = isPlaylistActive(playlist);
                const expirationText = playlist.expiration_date 
                    ? `${isExpired(playlist.expiration_date) ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`
                    : 'Sin fecha de expiración';
                    
                const playlistCard = document.createElement('div');
                playlistCard.className = 'col-md-4 mb-4';
                playlistCard.innerHTML = `
                    <div class="card playlist-card h-100 ${!active ? 'border-danger' : ''}">
                        <div class="card-body">
                            <h5 class="card-title">${playlist.title}</h5>
                            <p class="card-text">${playlist.description || 'Sin descripción'}</p>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="badge ${active ? 'bg-success' : 'bg-danger'}">
                                    ${active ? 'Activa' : 'Inactiva'}
                                </span>
                                <span class="badge bg-info">${expirationText}</span>
                            </div>
                            <div class="mt-2">
                                <span class="badge bg-secondary">${playlist.videos ? playlist.videos.length : 0} videos</span>
                            </div>
                        </div>
                        <div class="card-footer bg-transparent">
                            <button class="btn btn-primary btn-sm w-100" onclick="openPlaylistDetail(${playlist.id})">
                                Ver Detalles
                            </button>
                        </div>
                    </div>
                `;
                playlistsList.appendChild(playlistCard);
            });
        }
        
    } catch (error) {
        console.error('Error al cargar playlists:', error);
        
        // Mostrar mensaje de error
        playlistsList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5">
                    <div class="alert alert-danger">Error al cargar listas de reproducción: ${error.message}</div>
                </td>
            </tr>
        `;
        
        // Mostrar notificación
        showToast(`Error al cargar listas de reproducción: ${error.message}`, 'error');
    }
}

// Función para filtrar playlists por título o descripción
function filterPlaylistsByTitle(searchText) {
    console.log("Filtrando playlists por texto:", searchText);
    
    // Normalizar texto de búsqueda
    searchText = (searchText || '').toLowerCase().trim();
    
    // Obtener contenedor
    const playlistsList = document.getElementById('playlistsList');
    if (!playlistsList) {
        console.error("Elemento playlistsList no encontrado");
        return;
    }
    
    try {
        // Si no hay texto de búsqueda, mostrar todas las playlists
        if (!searchText) {
            const filterSelect = document.getElementById('playlistFilterStatus');
            const currentFilter = filterSelect ? filterSelect.value : 'all';
            loadPlaylists(currentFilter);
            return;
        }
        
        // Filtrar playlists
        const filteredPlaylists = allPlaylists.filter(playlist => 
            (playlist.title && playlist.title.toLowerCase().includes(searchText)) ||
            (playlist.description && playlist.description.toLowerCase().includes(searchText))
        );
        
        // Actualizar contador
        const playlistCountBadge = document.getElementById('playlistCountBadge');
        if (playlistCountBadge) {
            playlistCountBadge.textContent = `${filteredPlaylists.length} listas`;
        }
        
        // Determinar el modo de visualización actual
        const tableMode = playlistsList.closest('table') !== null;
        
        // Limpiar contenedor
        playlistsList.innerHTML = '';
        
        if (filteredPlaylists.length === 0) {
            if (tableMode) {
                playlistsList.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center py-5">
                            <p>No se encontraron listas con esos criterios de búsqueda.</p>
                        </td>
                    </tr>
                `;
            } else {
                playlistsList.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <p>No se encontraron listas con esos criterios de búsqueda.</p>
                    </div>
                `;
            }
            return;
        }
        
        // Mostrar playlists filtradas según el modo actual
        if (tableMode) {
            // Modo tabla
            filteredPlaylists.forEach(playlist => {
                const active = isPlaylistActive(playlist);
                const expirationText = playlist.expiration_date 
                    ? `${isExpired(playlist.expiration_date) ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`
                    : 'Sin fecha de expiración';
                    
                const row = document.createElement('tr');
                row.className = active ? '' : 'table-danger';
                
                row.innerHTML = `
                    <td>${playlist.title}</td>
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
                        <button class="btn btn-primary" onclick="openPlaylistDetail(${playlist.id})">
                            <i class="fas fa-eye"></i> Ver Detalles
                        </button>
                    </td>
                `;
                playlistsList.appendChild(row);
            });
        } else {
            // Modo tarjetas
            filteredPlaylists.forEach(playlist => {
                const active = isPlaylistActive(playlist);
                const expirationText = playlist.expiration_date 
                    ? `${isExpired(playlist.expiration_date) ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`
                    : 'Sin fecha de expiración';
                    
                const playlistCard = document.createElement('div');
                playlistCard.className = 'col-md-4 mb-4';
                playlistCard.innerHTML = `
                    <div class="card playlist-card h-100 ${!active ? 'border-danger' : ''}">
                        <div class="card-body">
                            <h5 class="card-title">${playlist.title}</h5>
                            <p class="card-text">${playlist.description || 'Sin descripción'}</p>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="badge ${active ? 'bg-success' : 'bg-danger'}">
                                    ${active ? 'Activa' : 'Inactiva'}
                                </span>
                                <span class="badge bg-info">${expirationText}</span>
                            </div>
                            <div class="mt-2">
                                <span class="badge bg-secondary">${playlist.videos ? playlist.videos.length : 0} videos</span>
                            </div>
                        </div>
                        <div class="card-footer bg-transparent">
                            <button class="btn btn-primary btn-sm w-100" onclick="openPlaylistDetail(${playlist.id})">
                                Ver Detalles
                            </button>
                        </div>
                    </div>
                `;
                playlistsList.appendChild(playlistCard);
            });
        }
    } catch (error) {
        console.error('Error al filtrar playlists:', error);
        showToast(`Error al filtrar listas: ${error.message}`, 'error');
    }
}

// Función para cargar playlists activas para Raspberry Pi
async function loadRaspberryActivePlaylists() {
    console.log("Cargando playlists activas para Raspberry Pi");
    
    const raspberryActiveList = document.getElementById('raspberryActiveList');
    if (!raspberryActiveList) {
        console.error("Elemento raspberryActiveList no encontrado");
        return;
    }
    
    try {
        // Mostrar indicador de carga
        raspberryActiveList.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <p class="mt-2">Cargando listas activas para Raspberry Pi...</p>
            </div>
        `;
        
        // Realizar petición a la API
        const response = await fetch(`${API_URL}/raspberry/playlists/active`);
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }
        
        // Procesar respuesta
        const activePlaylists = await response.json();
        console.log("Playlists activas para Raspberry Pi:", activePlaylists);
        
        // Limpiar contenedor
        raspberryActiveList.innerHTML = '';
        
        if (!Array.isArray(activePlaylists) || activePlaylists.length === 0) {
            raspberryActiveList.innerHTML = `
                <div class="alert alert-warning">
                    No hay listas de reproducción activas para dispositivos Raspberry Pi
                </div>
            `;
            return;
        }
        
        // Crear tabla
        const table = document.createElement('table');
        table.className = 'table table-striped';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Título</th>
                    <th>Expiración</th>
                    <th>Videos</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
            </tbody>
        `;
        
        const tbody = table.querySelector('tbody');
        
        // Añadir filas a la tabla
        activePlaylists.forEach(playlist => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${playlist.title}</td>
                <td>${playlist.expiration_date ? formatDate(playlist.expiration_date) : 'Sin expiración'}</td>
                <td>${playlist.videos ? playlist.videos.length : 0} videos</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="openPlaylistDetail(${playlist.id})">
                        <i class="fas fa-eye"></i> Ver
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        // Añadir tabla al contenedor
        raspberryActiveList.appendChild(table);
        
    } catch (error) {
        console.error('Error al cargar playlists activas para Raspberry Pi:', error);
        
        // Mostrar mensaje de error
        raspberryActiveList.innerHTML = `
            <div class="alert alert-danger">
                Error al cargar listas de reproducción activas: ${error.message}
            </div>
        `;
        
        // Mostrar notificación
        showToast(`Error al cargar listas activas para Raspberry Pi: ${error.message}`, 'error');
    }
}

// Función para abrir detalles de una playlist
async function openPlaylistDetail(playlistId) {
    console.log("Abriendo detalles de playlist:", playlistId);
    
    // Guardar el ID de la playlist actual
    currentPlaylistId = playlistId;
    
    try {
        // Mostrar indicador de carga en el modal
        const playlistInfo = document.getElementById('playlistInfo');
        if (playlistInfo) {
            playlistInfo.innerHTML = `
                <div class="text-center p-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Cargando detalles de la lista...</p>
                </div>
            `;
        }
        
        // Mostrar el modal
        const modalElement = document.getElementById('playlistDetailModal');
        if (modalElement && window.bootstrap) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        }
        
        // Realizar petición a la API
        const response = await fetch(`${API_URL}/playlists/${playlistId}`);
        
        if (!response.ok) {
            throw new Error(`Error al cargar detalles: ${response.status} ${response.statusText}`);
        }
        
        // Procesar respuesta
        const playlist = await response.json();
        console.log("Datos de playlist recibidos:", playlist);
        
        // Verificar que el modal existe y está visible
        if (!modalElement) {
            throw new Error("Modal de detalles no encontrado");
        }
        
        // Actualizar información en el modal
        updatePlaylistDetailModal(playlist);
        
    } catch (error) {
        console.error('Error al cargar detalles de la playlist:', error);
        
        // Ocultar modal si está abierto
        try {
            const modalElement = document.getElementById('playlistDetailModal');
            if (modalElement && window.bootstrap) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                }
            }
        } catch (e) {
            console.error("Error al cerrar modal:", e);
        }
        
        // Mostrar notificación
        showToast(`Error al cargar detalles de la lista: ${error.message}`, 'error');
    }
}

// Función para actualizar el modal con los detalles de la playlist
function updatePlaylistDetailModal(playlist) {
    try {
        // Actualizar título del modal
        const playlistDetailTitle = document.getElementById('playlistDetailTitle');
        if (playlistDetailTitle) {
            playlistDetailTitle.textContent = playlist.title || 'Sin título';
        }
        
        // Recuperar el contenedor principal de información
        const playlistInfo = document.getElementById('playlistInfo');
        if (!playlistInfo) {
            throw new Error("Contenedor de información no encontrado");
        }
        
        // Restaurar estructura del contenedor si fue reemplazada por el indicador de carga
        if (!document.getElementById('playlistDetailDescription')) {
            // Si la estructura fue reemplazada, recrearla
            playlistInfo.innerHTML = `
                <p id="playlistDetailDescription"></p>
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div>
                        <span class="badge bg-info" id="playlistDetailDate"></span>
                        <span class="badge" id="playlistDetailStatus"></span>
                        <span class="badge" id="playlistDetailExpirationDate"></span>
                    </div>
                    <div>
                        <button class="btn btn-outline-primary" id="editPlaylistBtn">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                        <button class="btn btn-success" id="playlistDownloadBtn">
                            <i class="fas fa-download"></i> Descargar Lista
                        </button>
                    </div>
                </div>
                
                <!-- Pestañas de navegación -->
                <ul class="nav nav-tabs mb-3" id="playlistDetailTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="videos-tab" data-bs-toggle="tab" data-bs-target="#videosTab" type="button" role="tab" aria-controls="videosTab" aria-selected="true">
                            Videos
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="devices-tab" data-bs-toggle="tab" data-bs-target="#devicesTab" type="button" role="tab" aria-controls="devicesTab" aria-selected="false">
                            Dispositivos
                        </button>
                    </li>
                </ul>
                
                <!-- Contenido de las pestañas -->
                <div class="tab-content" id="playlistDetailTabsContent">
                    <!-- Pestaña de Videos -->
                    <div class="tab-pane fade show active" id="videosTab" role="tabpanel" aria-labelledby="videos-tab">
                        <h6 class="mb-3">Videos en esta lista</h6>
                        <!-- Tabla de videos en lugar de lista -->
                        <div class="table-responsive">
                            <table class="table table-sm table-hover">
                                <thead>
                                    <tr>
                                        <th>Título</th>
                                        <th>Descripción</th>
                                        <th>Expiración</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody id="playlistVideos">
                                    <!-- Videos en la lista -->
                                </tbody>
                            </table>
                        </div>
                        
                        <hr class="my-4" />
                        
                        <h6>Agregar videos a esta lista</h6>
                        <div class="input-group input-group-lg mb-3">
                            <select class="form-select" id="addVideoSelect">
                                <option value="">Seleccionar video...</option>
                            </select>
                            <button class="btn btn-primary" id="addVideoBtn">Agregar Video</button>
                        </div>
                    </div>
                    
                    <!-- Pestaña de Dispositivos -->
                    <div class="tab-pane fade" id="devicesTab" role="tabpanel" aria-labelledby="devices-tab">
                        <h6 class="mb-3">Dispositivos asignados a esta lista</h6>
                        <div id="assignedDevicesContainer">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Cargando...</span>
                            </div>
                        </div>
                        
                        <hr class="my-4" />
                        
                        <h6>Asignar más dispositivos a esta lista</h6>
                        <div class="input-group input-group-lg mb-3">
                            <select class="form-select" id="addDeviceSelect">
                                <option value="">Seleccionar dispositivo...</option>
                            </select>
                            <button class="btn btn-primary" id="addDeviceBtn">Asignar Dispositivo</button>
                        </div>
                        
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle"></i> 
                            Los dispositivos asignados reproducirán automáticamente esta lista si está activa.
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Actualizar descripción
        const playlistDetailDescription = document.getElementById('playlistDetailDescription');
        if (playlistDetailDescription) {
            playlistDetailDescription.textContent = playlist.description || 'Sin descripción';
        }
        
        // Actualizar fecha de creación
        const playlistDetailDate = document.getElementById('playlistDetailDate');
        if (playlistDetailDate) {
            playlistDetailDate.textContent = `Creada: ${formatDate(playlist.creation_date)}`;
        }
        
        // Actualizar fecha de expiración
        const expirationBadge = document.getElementById('playlistDetailExpirationDate');
        if (expirationBadge) {
            if (playlist.expiration_date) {
                const expired = isExpired(playlist.expiration_date);
                expirationBadge.className = `badge ${expired ? 'bg-danger' : 'bg-info'}`;
                expirationBadge.textContent = `${expired ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`;
            } else {
                expirationBadge.className = 'badge bg-secondary';
                expirationBadge.textContent = 'Sin fecha de expiración';
            }
        }
        
        // Actualizar estado de la playlist
        const statusBadge = document.getElementById('playlistDetailStatus');
        if (statusBadge) {
            const isActive = isPlaylistActive(playlist);
            statusBadge.className = `badge ${isActive ? 'bg-success' : 'bg-danger'}`;
            statusBadge.textContent = isActive ? 'Activa' : 'Inactiva';
        }
        
        // Configurar botón de descarga
        const downloadBtn = document.getElementById('playlistDownloadBtn');
        if (downloadBtn) {
            downloadBtn.onclick = () => {
                window.location.href = `${API_URL}/playlists/${playlist.id}/download`;
            };
        }
        
        // Configurar botón de editar
        const editBtn = document.getElementById('editPlaylistBtn');
        if (editBtn) {
            editBtn.onclick = () => {
                preparePlaylistForEditing(playlist);
            };
        }
        
        // Configurar botón para eliminar playlist
        const deleteBtn = document.getElementById('deletePlaylistBtn');
        if (deleteBtn) {
            deleteBtn.onclick = () => {
                if (confirm('¿Estás seguro de que deseas eliminar esta lista de reproducción?')) {
                    deletePlaylist(playlist.id);
                }
            };
        }
        
        // Mostrar videos en la playlist
        const playlistVideos = document.getElementById('playlistVideos');
        if (playlistVideos) {
            playlistVideos.innerHTML = '';
            
            if (!playlist.videos || playlist.videos.length === 0) {
                playlistVideos.innerHTML = '<tr><td colspan="4" class="text-center">No hay videos en esta lista</td></tr>';
            } else {
                playlist.videos.forEach(video => {
                    const videoExpired = video.expiration_date && isExpired(video.expiration_date);
                    const videoRow = document.createElement('tr');
                    videoRow.className = videoExpired ? 'table-danger' : '';
                    
                    videoRow.innerHTML = `
                        <td>${video.title || 'Sin título'}</td>
                        <td>${video.description || '<span class="text-muted">Sin descripción</span>'}</td>
                        <td>
                            ${video.expiration_date ? 
                                `<span class="badge ${videoExpired ? 'bg-danger' : 'bg-info'}">
                                    ${videoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                                </span>` : 
                                '<span class="text-muted">Sin expiración</span>'}
                        </td>
                        <td>
                            <button class="btn btn-outline-danger" onclick="removeVideoFromPlaylist(${playlist.id}, ${video.id})">
                                <i class="fas fa-times"></i> Eliminar
                            </button>
                        </td>
                    `;
                    playlistVideos.appendChild(videoRow);
                });
            }
        }
        
        // Cargar videos disponibles para agregar
        loadAvailableVideosForPlaylist(playlist.id, playlist.videos || []);
        
        // Cargar dispositivos asignados a la playlist (si está implementado)
        if (typeof loadPlaylistDevices === 'function') {
            try {
                loadPlaylistDevices(playlist.id);
            } catch (err) {
                console.error("Error al cargar dispositivos de la playlist:", err);
            }
        }
        
        // Cargar dispositivos disponibles para asignar (si está implementado)
        if (typeof loadAvailableDevices === 'function') {
            try {
                loadAvailableDevices(playlist.id);
            } catch (err) {
                console.error("Error al cargar dispositivos disponibles:", err);
            }
        }
        
        // Configurar botón para agregar video
        const addVideoBtn = document.getElementById('addVideoBtn');
        if (addVideoBtn) {
            addVideoBtn.onclick = () => {
                const videoId = document.getElementById('addVideoSelect')?.value;
                if (videoId) {
                    addVideoToPlaylist(playlist.id, parseInt(videoId));
                } else {
                    showToast('Por favor, selecciona un video para agregar a la lista', 'error');
                }
            };
        }
        
        // Configurar botón para agregar dispositivo
        const addDeviceBtn = document.getElementById('addDeviceBtn');
        if (addDeviceBtn) {
            addDeviceBtn.onclick = () => {
                const deviceId = document.getElementById('addDeviceSelect')?.value;
                if (deviceId) {
                    addDeviceToPlaylist(playlist.id, deviceId);
                } else {
                    showToast('Por favor, selecciona un dispositivo para asignar a la lista', 'error');
                }
            };
        }
    } catch (error) {
        console.error('Error al actualizar modal de detalles:', error);
        showToast(`Error al mostrar detalles: ${error.message}`, 'error');
    }
}