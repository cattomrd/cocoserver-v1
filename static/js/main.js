// Configuración global
const API_URL = '/api'; // Cambiar según la configuración del servidor
let allVideos = [];
let allPlaylists = [];
let currentPlaylistId = null;

// Función para probar la conexión a la API
async function testApiConnection() {
    try {
        console.log("Probando conexión a API:", `${API_URL}/videos/`);
        const response = await fetch(`${API_URL}/videos/`);
        console.log("Estado de respuesta:", response.status);
        
        if (!response.ok) {
            console.error("La API no responde correctamente:", 
                        response.status, response.statusText);
            // Mostrar mensaje de error
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
        // Mostrar mensaje de error
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

// Llamar a esta función cuando se carga el documento
document.addEventListener('DOMContentLoaded', function() {
    // Otras inicializaciones...
    
    // Probar conexión a la API
    testApiConnection();
});

// Función para formatear fechas
function formatDate(dateString) {
    if (!dateString) return 'Sin fecha';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Verificar si una fecha ha expirado
function isExpired(dateString) {
    if (!dateString) return false;
    const expirationDate = new Date(dateString);
    const now = new Date();
    return expirationDate < now;
}

// Verificar si una playlist está activa
function isPlaylistActive(playlist) {
    if (!playlist.is_active) return false;
    if (playlist.expiration_date && isExpired(playlist.expiration_date)) return false;
    return true;
}

// Función para cargar videos
async function loadVideos(filter = 'all') {
    try {
        document.getElementById('videosLoading').style.display = 'block';
        
        // Añadir logging para depuración
        console.log("Solicitando videos desde:", `${API_URL}/videos/`);
        
        const response = await fetch(`${API_URL}/videos/`);
        console.log("Respuesta de la API:", response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error("Error en respuesta:", errorText);
            throw new Error(`Error de servidor: ${response.status} - ${response.statusText}`);
        }
        
        const responseData = await response.json();
        console.log("Datos recibidos:", responseData);
        
        allVideos = responseData;
        
        const videosList = document.getElementById('videosList');
        videosList.innerHTML = '';
        
        // Verificar si tenemos datos válidos
        if (!Array.isArray(allVideos)) {
            console.error("Datos recibidos no son un array:", allVideos);
            throw new Error("Formato de datos inválido");
        }
        
        // Filtrar videos según el criterio seleccionado
        let filteredVideos = allVideos;
        if (filter === 'active') {
            filteredVideos = allVideos.filter(video => !video.expiration_date || !isExpired(video.expiration_date));
        } else if (filter === 'expired') {
            filteredVideos = allVideos.filter(video => video.expiration_date && isExpired(video.expiration_date));
        }
        
        if (filteredVideos.length === 0) {
            videosList.innerHTML = `
                <div class="col-12 text-center py-5">
                    <p>No hay videos disponibles. ¡Sube tu primer video!</p>
                </div>
            `;
            return;
        }
        
        filteredVideos.forEach(video => {
            const isVideoExpired = video.expiration_date && isExpired(video.expiration_date);
            const videoCard = document.createElement('div');
            videoCard.className = 'col-md-4 mb-4';
            videoCard.innerHTML = `
                <div class="card h-100 ${isVideoExpired ? 'border-danger' : ''}">
                    <div class="card-img-top bg-dark d-flex align-items-center justify-content-center" style="height: 180px;">
                        <i class="fas fa-film" style="font-size: 3rem; color: #aaa;"></i>
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">${video.title}</h5>
                        <p class="card-text small">${video.description || 'Sin descripción'}</p>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <small class="text-muted">Subido: ${formatDate(video.upload_date)}</small>
                        </div>
                        ${video.expiration_date ? 
                            `<div class="mb-2">
                                <span class="badge ${isVideoExpired ? 'bg-danger' : 'bg-info'}">
                                    ${isVideoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                                </span>
                            </div>` : ''}
                        <div class="d-flex justify-content-between mt-3">
                            <a href="${API_URL}/videos/${video.id}/download" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-download"></i> Descargar
                            </a>
                            <button class="btn btn-sm btn-outline-secondary" onclick="editVideo(${video.id})">
                                <i class="fas fa-edit"></i> Editar
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteVideo(${video.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            videosList.appendChild(videoCard);
        });
    } catch (error) {
        console.error('Error al cargar videos:', error);
        document.getElementById('videosList').innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="alert alert-danger">Error al cargar videos: ${error.message}</div>
            </div>
        `;
    } finally {
        document.getElementById('videosLoading').style.display = 'none';
    }
}
// Función para cargar los dispositivos asignados a una playlist
async function loadPlaylistDevices(playlistId) {
    console.log("Cargando dispositivos para playlist:", playlistId); // Debug

    try {
        // Mostrar indicador de carga en el contenedor de dispositivos
        const devicesContainer = document.getElementById('assignedDevicesContainer');
        if (devicesContainer) {
            devicesContainer.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <span class="ms-2">Cargando dispositivos asignados...</span>
                </div>
            `;
        }

        // Realizar la petición a la API para obtener los dispositivos asignados
        const response = await fetch(`/api/device-playlists/playlist/${playlistId}/devices`);
        
        if (!response.ok) {
            throw new Error(`Error al cargar dispositivos asignados: ${response.status} ${response.statusText}`);
        }
        
        const assignedDevices = await response.json();
        console.log("Dispositivos asignados recibidos:", assignedDevices); // Debug
        
        // Verificar si el contenedor existe
        if (!devicesContainer) {
            console.error("No se encontró el contenedor de dispositivos asignados");
            return;
        }
        
        // Mostrar mensaje si no hay dispositivos asignados
        if (!assignedDevices || assignedDevices.length === 0) {
            devicesContainer.innerHTML = '<p class="text-center">No hay dispositivos asignados a esta lista</p>';
            return;
        }
        
        // Crear la lista de dispositivos asignados
        const devicesList = document.createElement('div');
        devicesList.className = 'list-group';
        
        // Iterar sobre los dispositivos asignados
        assignedDevices.forEach(device => {
            const deviceItem = document.createElement('div');
            deviceItem.className = `list-group-item list-group-item-action d-flex justify-content-between align-items-center ${device.is_active ? '' : 'list-group-item-warning'}`;
            deviceItem.innerHTML = `
                <div>
                    <h6 class="mb-1">${device.name || 'Sin nombre'} (${device.device_id || 'ID desconocido'})</h6>
                    <small>${device.location || ''} ${device.tienda ? ' - ' + device.tienda : ''}</small>
                    <div>
                        <span class="badge ${device.is_active ? 'bg-success' : 'bg-danger'}">
                            ${device.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                    </div>
                </div>
                <button class="btn btn-sm btn-outline-danger remove-device-btn" data-device-id="${device.device_id}" data-playlist-id="${playlistId}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            devicesList.appendChild(deviceItem);
        });
        
        // Limpiar el contenedor y añadir la lista
        devicesContainer.innerHTML = '';
        devicesContainer.appendChild(devicesList);
        
        // Añadir event listeners a los botones de eliminar
        const removeButtons = devicesContainer.querySelectorAll('.remove-device-btn');
        removeButtons.forEach(button => {
            button.addEventListener('click', function() {
                const deviceId = this.getAttribute('data-device-id');
                const playlistId = this.getAttribute('data-playlist-id');
                if (confirm(`¿Estás seguro de que deseas quitar el dispositivo ${deviceId} de esta lista?`)) {
                    removeDeviceFromPlaylist(deviceId, parseInt(playlistId));
                }
            });
        });
    } catch (error) {
        console.error('Error al cargar dispositivos asignados:', error);
        const devicesContainer = document.getElementById('assignedDevicesContainer');
        if (devicesContainer) {
            devicesContainer.innerHTML = `<div class="alert alert-danger">Error al cargar dispositivos: ${error.message}</div>`;
        }
    }
}
// Función para cargar playlists
async function loadPlaylists(filter = 'all') {
    try {
        const response = await fetch(`${API_URL}/playlists/`);
        if (!response.ok) throw new Error('Error al cargar playlists');
        
        allPlaylists = await response.json();
        
        const playlistsList = document.getElementById('playlistsList');
        playlistsList.innerHTML = '';
        
        // Filtrar playlists según el criterio seleccionado
        let filteredPlaylists = allPlaylists;
        if (filter === 'active') {
            filteredPlaylists = allPlaylists.filter(playlist => isPlaylistActive(playlist));
        } else if (filter === 'inactive') {
            filteredPlaylists = allPlaylists.filter(playlist => !isPlaylistActive(playlist));
        }
        
        if (filteredPlaylists.length === 0) {
            playlistsList.innerHTML = `
                <div class="col-12 text-center py-5">
                    <p>No hay listas de reproducción disponibles. ¡Crea tu primera lista!</p>
                </div>
            `;
            return;
        }
        
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
                            <span class="badge bg-secondary">${playlist.videos.length} videos</span>
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
    } catch (error) {
        console.error('Error al cargar playlists:', error);
        document.getElementById('playlistsList').innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="alert alert-danger">Error al cargar listas de reproducción: ${error.message}</div>
            </div>
        `;
    } finally {
        document.getElementById('playlistsLoading').style.display = 'none';
    }
}

// Función para cargar playlists activas para Raspberry Pi
async function loadRaspberryActivePlaylists() {
    try {
        const response = await fetch(`${API_URL}/raspberry/playlists/active`);
        if (!response.ok) throw new Error('Error al cargar playlists activas');
        
        const activePlaylists = await response.json();
        
        const raspberryActiveList = document.getElementById('raspberryActiveList');
        raspberryActiveList.innerHTML = '';
        
        if (activePlaylists.length === 0) {
            raspberryActiveList.innerHTML = `
                <div class="alert alert-warning">
                    No hay listas de reproducción activas para dispositivos Raspberry Pi
                </div>
            `;
            return;
        }
        
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
        
        activePlaylists.forEach(playlist => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${playlist.title}</td>
                <td>${playlist.expiration_date ? formatDate(playlist.expiration_date) : 'Sin expiración'}</td>
                <td>${playlist.videos.length} videos</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="openPlaylistDetail(${playlist.id})">
                        <i class="fas fa-eye"></i> Ver
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        raspberryActiveList.appendChild(table);
        
    } catch (error) {
        console.error('Error al cargar playlists activas para Raspberry Pi:', error);
        document.getElementById('raspberryActiveList').innerHTML = `
            <div class="alert alert-danger">
                Error al cargar listas de reproducción activas: ${error.message}
            </div>
        `;
    }
}

// Abrir detalles de playlist
// Función mejorada para abrir y mostrar los detalles de una playlist
async function openPlaylistDetail(playlistId) {
    console.log("Abriendo detalles de playlist:", playlistId); // Debug
    
    // Guardar el ID de la playlist actual
    currentPlaylistId = playlistId;
    
    try {
        // Mostrar indicador de carga
        const playlistInfo = document.getElementById('playlistInfo');
        if (playlistInfo) {
            playlistInfo.innerHTML = `
                <div class="text-center p-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Cargando detalles de la playlist...</p>
                </div>
            `;
        }
        
        // Realizar la petición a la API
        const response = await fetch(`/api/playlists/${playlistId}`);
        
        if (!response.ok) {
            throw new Error(`Error al cargar detalles: ${response.status} ${response.statusText}`);
        }
        
        const playlist = await response.json();
        console.log("Datos de playlist recibidos:", playlist); // Debug
        
        // Actualizar título del modal
        const playlistDetailTitle = document.getElementById('playlistDetailTitle');
        if (playlistDetailTitle) {
            playlistDetailTitle.textContent = playlist.title || 'Sin título';
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
                window.location.href = `/api/playlists/${playlistId}/download`;
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
                    deletePlaylist(playlistId);
                }
            };
        }
        
        // Mostrar videos en la playlist
        const playlistVideos = document.getElementById('playlistVideos');
        if (playlistVideos) {
            playlistVideos.innerHTML = '';
            
            if (!playlist.videos || playlist.videos.length === 0) {
                playlistVideos.innerHTML = '<p class="text-center">No hay videos en esta lista</p>';
            } else {
                playlist.videos.forEach(video => {
                    const videoExpired = video.expiration_date && isExpired(video.expiration_date);
                    const videoItem = document.createElement('div');
                    videoItem.className = `list-group-item list-group-item-action d-flex justify-content-between align-items-center ${videoExpired ? 'list-group-item-danger' : ''}`;
                    videoItem.innerHTML = `
                        <div>
                            <h6 class="mb-1">${video.title || 'Sin título'}</h6>
                            <small>${video.description || 'Sin descripción'}</small>
                            ${video.expiration_date ? 
                                `<div>
                                    <span class="badge ${videoExpired ? 'bg-danger' : 'bg-info'}">
                                        ${videoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                                    </span>
                                </div>` : ''}
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="removeVideoFromPlaylist(${playlistId}, ${video.id})">
                            <i class="fas fa-times"></i>
                        </button>
                    `;
                    playlistVideos.appendChild(videoItem);
                });
            }
        }
        
        // Cargar videos disponibles para agregar
        const addVideoSelect = document.getElementById('addVideoSelect');
        if (addVideoSelect) {
            addVideoSelect.innerHTML = '<option value="">Seleccionar video...</option>';
            
            // Asegurarnos de que allVideos esté disponible
            if (!allVideos || allVideos.length === 0) {
                try {
                    const videosResponse = await fetch('/api/videos/');
                    if (videosResponse.ok) {
                        allVideos = await videosResponse.json();
                    }
                } catch (err) {
                    console.error("Error al cargar videos:", err);
                }
            }
            
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
                    availableVideos.forEach(video => {
                        const option = document.createElement('option');
                        option.value = video.id;
                        option.textContent = video.title;
                        addVideoSelect.appendChild(option);
                    });
                }
            } else {
                addVideoSelect.innerHTML += '<option disabled>No hay videos disponibles</option>';
            }
        }
        
        // Configurar botón para agregar video
        const addVideoBtn = document.getElementById('addVideoBtn');
        if (addVideoBtn) {
            addVideoBtn.onclick = () => {
                const videoId = addVideoSelect.value;
                if (videoId) {
                    addVideoToPlaylist(playlistId, parseInt(videoId));
                } else {
                    alert('Por favor, selecciona un video para agregar a la lista');
                }
            };
        }

        // Cargar dispositivos asignados a la playlist (si está implementado)
        if (typeof loadPlaylistDevices === 'function') {
            try {
                await loadPlaylistDevices(playlistId);
            } catch (err) {
                console.error("Error al cargar dispositivos de la playlist:", err);
            }
        }
        
        // Cargar dispositivos disponibles para asignar (si está implementado)
        if (typeof loadAvailableDevices === 'function') {
            try {
                await loadAvailableDevices(playlistId);
            } catch (err) {
                console.error("Error al cargar dispositivos disponibles:", err);
            }
        }
        
        // Mostrar el modal
        const modal = document.getElementById('playlistDetailModal');
        if (modal) {
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
        } else {
            console.error("No se encontró el modal de detalles de playlist");
            alert("Error: No se pudo mostrar los detalles de la playlist");
        }
        
    } catch (error) {
        console.error('Error al cargar detalles de la playlist:', error);
        alert(`Error al cargar los detalles de la lista de reproducción: ${error.message}`);
    }
}

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
        return date.toLocaleString();
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

// Preparar playlist para edición
function preparePlaylistForEditing(playlist) {
    console.log("Preparando playlist para edición:", playlist); // Debug
    
    // Verificar que existan los elementos necesarios
    const editIdInput = document.getElementById('editPlaylistId');
    const editTitleInput = document.getElementById('editPlaylistTitle');
    const editDescriptionInput = document.getElementById('editPlaylistDescription');
    const editExpirationInput = document.getElementById('editPlaylistExpiration');
    const editActiveCheckbox = document.getElementById('editPlaylistActive');
    
    if (!editIdInput || !editTitleInput || !editDescriptionInput || !editExpirationInput || !editActiveCheckbox) {
        console.error("No se encontraron todos los campos del formulario de edición");
        alert("Error: No se encontraron los campos del formulario de edición. Por favor, contacte al administrador.");
        return;
    }
    
    // Asignar valores a los campos
    editIdInput.value = playlist.id;
    editTitleInput.value = playlist.title;
    editDescriptionInput.value = playlist.description || '';
    
    // Formatear fecha para el input datetime-local
    if (playlist.expiration_date) {
        const date = new Date(playlist.expiration_date);
        // Asegurarse de que la zona horaria se maneje correctamente
        const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
            .toISOString()
            .slice(0, 16);
        editExpirationInput.value = localDatetime;
    } else {
        editExpirationInput.value = '';
    }
    
    editActiveCheckbox.checked = playlist.is_active;
    
    // Buscar los modales en el DOM
    const detailModal = document.getElementById('playlistDetailModal');
    const editModal = document.getElementById('editPlaylistModal');
    
    if (!detailModal || !editModal) {
        console.error("No se encontraron los modales necesarios");
        alert("Error: No se encontraron los modales necesarios. Por favor, contacte al administrador.");
        return;
    }
     // Cerrar modal de detalles
    try {
        const detailModalInstance = bootstrap.Modal.getInstance(detailModal);
        if (detailModalInstance) {
            detailModalInstance.hide();
        } else {
            console.warn("No se pudo obtener la instancia del modal de detalles");
        }
    } catch (error) {
        console.error("Error al cerrar el modal de detalles:", error);
    }
    
    // Mostrar modal de edición después de un breve retardo
    setTimeout(() => {
        try {
            const editModalInstance = new bootstrap.Modal(editModal);
            editModalInstance.show();
        } catch (error) {
            console.error("Error al mostrar el modal de edición:", error);
            alert("Error al abrir el formulario de edición. Por favor, inténtelo de nuevo.");
        }
    }, 300);
}

// Editar video
async function editVideo(videoId) {
    console.log("Editando video:", videoId); // Debug
    
    try {
        // Buscar el video en los datos cargados
        const video = allVideos.find(v => v.id === videoId);
        if (!video) {
            throw new Error('Video no encontrado en los datos cargados');
        }
        
        console.log("Datos del video a editar:", video); // Debug
        
        // Verificar que existen los elementos del formulario
        const editIdInput = document.getElementById('editVideoId');
        const editTitleInput = document.getElementById('editVideoTitle');
        const editDescriptionInput = document.getElementById('editVideoDescription');
        const editExpirationInput = document.getElementById('editVideoExpiration');
        
        if (!editIdInput || !editTitleInput || !editDescriptionInput || !editExpirationInput) {
            throw new Error('No se encontraron todos los elementos del formulario de edición');
        }
        
        // Asignar los valores actuales a los campos del formulario
        editIdInput.value = video.id;
        editTitleInput.value = video.title || '';
        editDescriptionInput.value = video.description || '';
        
        // Formatear fecha de expiración para el input datetime-local
        if (video.expiration_date) {
            try {
                const date = new Date(video.expiration_date);
                // Verificar que la fecha es válida
                if (!isNaN(date.getTime())) {
                    // Formato para datetime-local (YYYY-MM-DDThh:mm)
                    const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                        .toISOString()
                        .slice(0, 16);
                    editExpirationInput.value = localDatetime;
                } else {
                    console.warn("Fecha de expiración inválida:", video.expiration_date);
                    editExpirationInput.value = '';
                }
            } catch (e) {
                console.error("Error al procesar fecha de expiración:", e);
                editExpirationInput.value = '';
            }
        } else {
            editExpirationInput.value = '';
        }
        
        // Mostrar el modal de edición
        const editModal = document.getElementById('editVideoModal');
        if (!editModal) {
            throw new Error('No se encontró el modal de edición de videos');
        }
        
        const modal = new bootstrap.Modal(editModal);
        modal.show();
        
    } catch (error) {
        console.error('Error al preparar el video para edición:', error);
        alert(`Error: ${error.message}`);
    }
}

async function saveVideoChanges() {
    console.log("Guardando cambios del video..."); // Debug
    
    try {
        // Verificar que existen los elementos del formulario
        const editIdInput = document.getElementById('editVideoId');
        const editTitleInput = document.getElementById('editVideoTitle');
        const editDescriptionInput = document.getElementById('editVideoDescription');
        const editExpirationInput = document.getElementById('editVideoExpiration');
        
        if (!editIdInput || !editTitleInput || !editDescriptionInput || !editExpirationInput) {
            throw new Error('No se encontraron todos los elementos del formulario de edición');
        }
        
        const videoId = editIdInput.value;
        if (!videoId) {
            throw new Error('ID de video no válido');
        }
        
        // Recopilar datos del formulario
        const videoData = {
            title: editTitleInput.value,
            description: editDescriptionInput.value || null,
            expiration_date: editExpirationInput.value || null
        };
        
        console.log("Enviando datos para actualizar video:", videoData); // Debug
        console.log("URL de la petición:", `/api/videos/${videoId}`); // Debug
        
        // Enviar la petición a la API
        const response = await fetch(`/api/videos/${videoId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(videoData),
        });
        
        // Verificar si la petición fue exitosa
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Error en la respuesta del servidor: ${response.status} ${response.statusText}`);
        }
        
        console.log("Respuesta del servidor:", response.status); // Debug
        
        // Obtener los datos actualizados
        const updatedVideo = await response.json();
        console.log("Video actualizado:", updatedVideo); // Debug
        
        // Mostrar mensaje de éxito
        alert('Video actualizado correctamente');
        
        // Cerrar el modal de edición
        const editModal = document.getElementById('editVideoModal');
        if (editModal) {
            const modalInstance = bootstrap.Modal.getInstance(editModal);
            if (modalInstance) {
                modalInstance.hide();
            } else {
                console.warn("No se pudo obtener la instancia del modal de edición");
            }
        }
        
        // Actualizar la lista de videos
        await loadVideos();
        
    } catch (error) {
        console.error('Error al guardar cambios del video:', error);
        alert(`Error: ${error.message}`);
    }
}

// Configurar event listener para el botón de guardar cambios
document.addEventListener('DOMContentLoaded', function() {
    console.log("Configurando event listeners para edición de videos"); // Debug
    
    const saveVideoChangesBtn = document.getElementById('saveVideoChangesBtn');
    if (saveVideoChangesBtn) {
        console.log("Encontrado botón saveVideoChangesBtn - configurando handler"); // Debug
        
        saveVideoChangesBtn.addEventListener('click', function() {
            console.log("Botón saveVideoChangesBtn clickeado"); // Debug
            saveVideoChanges();
        });
    } else {
        console.warn("No se encontró el botón saveVideoChangesBtn"); // Debug
    }
});

// Añadir método de respaldo para manejar los clics en el botón de editar
document.addEventListener('click', function(event) {
    // Verificar si el elemento clickeado o alguno de sus padres tiene 'data-action="edit-video"'
    const editButton = event.target.closest('[data-action="edit-video"]');
    if (editButton) {
        const videoId = parseInt(editButton.getAttribute('data-video-id'));
        if (videoId) {
            console.log("Botón editar video clickeado usando el manejador alternativo, ID:", videoId); // Debug
            editVideo(videoId);
        }
    }
});

// Guardar cambios de la playlist
async function savePlaylistChanges() {
    try {
        console.log("Guardando cambios de playlist..."); // Debug
        
        const editIdInput = document.getElementById('editPlaylistId');
        if (!editIdInput || !editIdInput.value) {
            throw new Error("No se ha definido ID de playlist para editar");
        }
        
        const playlistId = editIdInput.value;
        
        // Obtener los valores de los campos del formulario
        const playlistData = {
            title: document.getElementById('editPlaylistTitle').value,
            description: document.getElementById('editPlaylistDescription').value || null,
            expiration_date: document.getElementById('editPlaylistExpiration').value || null,
            is_active: document.getElementById('editPlaylistActive').checked
        };
        
        console.log("Enviando datos:", playlistData, "a URL:", `/api/playlists/${playlistId}`); // Debug
        
        // Realizar la petición al servidor
        const response = await fetch(`/api/playlists/${playlistId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(playlistData),
        });
        
        console.log("Respuesta del servidor:", response.status); // Debug
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
        }
        
        const updatedPlaylist = await response.json();
        console.log("Playlist actualizada:", updatedPlaylist); // Debug
        
        alert('Lista de reproducción actualizada correctamente');
        
        // Cerrar el modal de edición
        const editModal = document.getElementById('editPlaylistModal');
        if (editModal) {
            const editModalInstance = bootstrap.Modal.getInstance(editModal);
            if (editModalInstance) {
                editModalInstance.hide();
            } else {
                console.warn("No se pudo obtener la instancia del modal de edición");
            }
        }
        
        // Recargar playlists y abrir detalles
        try {
            await loadPlaylists();
            await openPlaylistDetail(parseInt(playlistId));
        } catch (error) {
            console.error("Error al recargar datos después de la actualización:", error);
            // Recargar la página como fallback
            window.location.reload();
        }
        
    } catch (error) {
        console.error('Error al guardar cambios de la playlist:', error);
        alert(`Error: ${error.message}`);
    }
}

// 3. Asegúrate de que el event listener para el botón de guardar esté configurado
document.addEventListener('DOMContentLoaded', function() {
    console.log("Configurando event listeners para edición de playlists..."); // Debug
    
    // Para el botón de editar en la vista de detalles
    const editPlaylistBtn = document.getElementById('editPlaylistBtn');
    if (editPlaylistBtn) {
        console.log("Configurando botón editPlaylistBtn"); // Debug
        
        editPlaylistBtn.addEventListener('click', function() {
            console.log("Botón editar playlist clickeado"); // Debug
            
            // Obtener la playlist actual desde los datos mostrados
            const playlistId = currentPlaylistId; // Asegúrate de que esta variable global existe
            
            if (!playlistId) {
                console.error("No se ha definido currentPlaylistId");
                alert("Error: No se pudo identificar la lista de reproducción a editar.");
                return;
            }
            
            // Buscar la playlist en el array de todas las playlists
            const playlist = allPlaylists.find(p => p.id === parseInt(playlistId));
            
            if (!playlist) {
                console.error("No se encontró la playlist con ID:", playlistId);
                alert("Error: No se encontró la lista de reproducción a editar.");
                return;
            }
            
            preparePlaylistForEditing(playlist);
        });
    } else {
        console.warn("No se encontró el botón editPlaylistBtn"); // Debug
    }
    
    // Para el botón de guardar cambios en el modal de edición
    const savePlaylistChangesBtn = document.getElementById('savePlaylistChangesBtn');
    if (savePlaylistChangesBtn) {
        console.log("Configurando botón savePlaylistChangesBtn"); // Debug
        
        savePlaylistChangesBtn.addEventListener('click', function() {
            console.log("Botón guardar cambios clickeado"); // Debug
            savePlaylistChanges();
        });
    } else {
        console.warn("No se encontró el botón savePlaylistChangesBtn"); // Debug
    }
});
// Subir un video
async function uploadVideo(formData) {
    const progressBar = document.querySelector('#uploadProgress .progress-bar');
    document.getElementById('uploadProgress').classList.remove('d-none');
    
    try {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_URL}/videos/`, true);
        
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percentComplete + '%';
                progressBar.textContent = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
            }
        };
        
        xhr.onload = function() {
            if (xhr.status === 200 || xhr.status === 201) {
                alert('Video subido correctamente');
                document.getElementById('videoUploadForm').reset();
                loadVideos();
            } else {
                let errorMessage = 'Error al subir el video';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.detail || errorMessage;
                } catch (e) {}
                alert(errorMessage);
            }
            document.getElementById('uploadProgress').classList.add('d-none');
        };
        
        xhr.onerror = function() {
            alert('Error de red al intentar subir el video');
            document.getElementById('uploadProgress').classList.add('d-none');
        };
        
        xhr.send(formData);
        
    } catch (error) {
        console.error('Error al subir video:', error);
        alert(`Error al subir el video: ${error.message}`);
        document.getElementById('uploadProgress').classList.add('d-none');
    }
}

// Crear una playlist
async function createPlaylist(playlistData) {
    try {
        const response = await fetch(`${API_URL}/playlists/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(playlistData),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al crear la lista');
        }
        
        alert('Lista de reproducción creada correctamente');
        document.getElementById('playlistCreateForm').reset();
        loadPlaylists();
        
    } catch (error) {
        console.error('Error al crear playlist:', error);
        alert(`Error al crear la lista de reproducción: ${error.message}`);
    }
}

// Eliminar un video
async function deleteVideo(videoId) {
    if (!confirm('¿Estás seguro de que deseas eliminar este video? Esta acción no se puede deshacer.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/videos/${videoId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al eliminar el video');
        }
        
        alert('Video eliminado correctamente');
        loadVideos();
        
    } catch (error) {
        console.error('Error al eliminar video:', error);
        alert(`Error al eliminar el video: ${error.message}`);
    }
}

// Eliminar una playlist
async function deletePlaylist(playlistId) {
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al eliminar la lista');
        }
        
        alert('Lista de reproducción eliminada correctamente');
        loadPlaylists();
        bootstrap.Modal.getInstance(document.getElementById('playlistDetailModal')).hide();
        
    } catch (error) {
        console.error('Error al eliminar playlist:', error);
        alert(`Error al eliminar la lista de reproducción: ${error.message}`);
    }
}

// Agregar video a playlist
async function addVideoToPlaylist(playlistId, videoId) {
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}/videos/${videoId}`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al añadir el video');
        }
        
        alert('Video añadido a la lista correctamente');
        openPlaylistDetail(playlistId); // Recargar detalles
        
    } catch (error) {
        console.error('Error al añadir video a playlist:', error);
        alert(`Error al añadir el video a la lista: ${error.message}`);
    }
}

// Eliminar video de playlist
async function removeVideoFromPlaylist(playlistId, videoId) {
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}/videos/${videoId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al eliminar el video');
        }
        
        alert('Video eliminado de la lista correctamente');
        openPlaylistDetail(playlistId); // Recargar detalles
        
    } catch (error) {
        console.error('Error al eliminar video de playlist:', error);
        alert(`Error al eliminar el video de la lista: ${error.message}`);
    }
}

// Event listeners - Se ejecutan cuando el DOM está completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Cargar videos y playlists inicialmente
    loadVideos();
    loadPlaylists();
    
    // Manejar navegación por pestañas
    document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const target = e.target.getAttribute('href');
            if (target === '#raspberry') {
                loadRaspberryActivePlaylists();
            }
        });
    });
    
    // Filtrar videos por estado
    document.getElementById('videoFilterExpiration').addEventListener('change', function() {
        loadVideos(this.value);
    });
    
    // Filtrar playlists por estado
    document.getElementById('playlistFilterStatus').addEventListener('change', function() {
        loadPlaylists(this.value);
    });
    
    // Formulario de subida de video
    document.getElementById('videoUploadForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        // Agregar fecha de expiración si se ha especificado
        const expirationDate = document.getElementById('videoExpiration').value;
        if (expirationDate) {
            formData.append('expiration_date', expirationDate);
        }
        
        uploadVideo(formData);
    });
    
    // Formulario de creación de playlist
    document.getElementById('playlistCreateForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const playlistData = {
            title: document.getElementById('playlistTitle').value,
            description: document.getElementById('playlistDescription').value || null,
            expiration_date: document.getElementById('playlistExpiration').value || null,
            is_active: document.getElementById('playlistActive').checked
        };
        
        createPlaylist(playlistData);
    });
    
    // Guardar cambios de playlist
    document.getElementById('savePlaylistChangesBtn').addEventListener('click', savePlaylistChanges);
    
    // Guardar cambios de video
    document.getElementById('saveVideoChangesBtn').addEventListener('click', saveVideoChanges);
    
    // Verificar estado de playlists automáticamente cada minuto
    setInterval(() => {
        const activeTab = document.querySelector('.nav-link.active').getAttribute('href');
        if (activeTab === '#playlists') {
            const filterValue = document.getElementById('playlistFilterStatus').value;
            loadPlaylists(filterValue);
        } else if (activeTab === '#videos') {
            const filterValue = document.getElementById('videoFilterExpiration').value;
            loadVideos(filterValue);
        } else if (activeTab === '#raspberry') {
            loadRaspberryActivePlaylists();
        }
    }, 60000); // 60 segundos
});

// Modificaciones a static/js/main.js para manejar la asociación de dispositivos a playlists

// Función para cargar los dispositivos asignados a una playlist



// Función para cargar dispositivos disponibles para asignar
async function loadAvailableDevices(playlistId) {
    console.log("Cargando dispositivos disponibles para playlist:", playlistId); // Debug
    
    try {
        // Obtener todos los dispositivos activos
        const allDevicesResponse = await fetch(`/api/devices/?active_only=true`);
        if (!allDevicesResponse.ok) {
            throw new Error(`Error al cargar dispositivos: ${allDevicesResponse.status} ${allDevicesResponse.statusText}`);
        }
        const allDevices = await allDevicesResponse.json();
        console.log("Todos los dispositivos:", allDevices); // Debug
        
        // Obtener dispositivos ya asignados
        const assignedDevicesResponse = await fetch(`/api/device-playlists/playlist/${playlistId}/devices`);
        if (!assignedDevicesResponse.ok) {
            throw new Error(`Error al cargar dispositivos asignados: ${assignedDevicesResponse.status} ${assignedDevicesResponse.statusText}`);
        }
        const assignedDevices = await assignedDevicesResponse.json();
        console.log("Dispositivos ya asignados:", assignedDevices); // Debug
        
        // Filtrar dispositivos que no están asignados
        const assignedDeviceIds = new Set(assignedDevices.map(d => d.device_id));
        const availableDevices = allDevices.filter(device => !assignedDeviceIds.has(device.device_id));
        console.log("Dispositivos disponibles para asignar:", availableDevices); // Debug
        
        // Actualizar el select de dispositivos disponibles
        const addDeviceSelect = document.getElementById('addDeviceSelect');
        if (!addDeviceSelect) {
            console.error("No se encontró el select para añadir dispositivos");
            return;
        }
        
        // Limpiar y añadir opción por defecto
        addDeviceSelect.innerHTML = '<option value="">Seleccionar dispositivo...</option>';
        
        if (availableDevices.length === 0) {
            addDeviceSelect.innerHTML += '<option disabled>No hay dispositivos disponibles para asignar</option>';
        } else {
            availableDevices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.device_id;
                option.textContent = `${device.name || 'Sin nombre'} (${device.device_id})`;
                if (device.location || device.tienda) {
                    option.textContent += ` - ${device.location || ''} ${device.tienda ? ' - ' + device.tienda : ''}`;
                }
                addDeviceSelect.appendChild(option);
            });
        }
        
    } catch (error) {
        console.error('Error al cargar dispositivos disponibles:', error);
        const addDeviceSelect = document.getElementById('addDeviceSelect');
        if (addDeviceSelect) {
            addDeviceSelect.innerHTML = '<option value="">Error al cargar dispositivos</option>';
        }
    }
}

// Función para asignar un dispositivo a una playlist
async function addDeviceToPlaylist(playlistId, deviceId) {
    try {
        const response = await fetch(`${API_URL}/device-playlists/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_id: deviceId,
                playlist_id: playlistId
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al asignar el dispositivo');
        }
        
        alert('Dispositivo asignado a la lista correctamente');
        
        // Recargar los dispositivos
        await loadPlaylistDevices(playlistId);
        await loadAvailableDevices(playlistId);
        
    } catch (error) {
        console.error('Error al asignar dispositivo a playlist:', error);
        alert(`Error al asignar el dispositivo a la lista: ${error.message}`);
    }
}
// Función para eliminar un dispositivo de una playlist
async function removeDeviceFromPlaylist(deviceId, playlistId) {
    console.log(`Eliminando dispositivo ${deviceId} de playlist ${playlistId}`); // Debug
    
    try {
        // Verificar que tenemos los datos necesarios
        if (!playlistId || !deviceId) {
            throw new Error("Faltan datos para la eliminación");
        }
        
        // Enviar la petición a la API
        const response = await fetch(`/api/device-playlists/${deviceId}/${playlistId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Error al eliminar la asignación: ${response.status} ${response.statusText}`);
        }
        
        alert('Dispositivo eliminado de la lista correctamente');
        
        // Recargar los dispositivos
        await loadPlaylistDevices(playlistId);
        await loadAvailableDevices(playlistId);
        
    } catch (error) {
        console.error('Error al eliminar dispositivo de playlist:', error);
        alert(`Error al eliminar el dispositivo de la lista: ${error.message}`);
    }
}

// Configurar event listener para el botón de añadir dispositivo
document.addEventListener('DOMContentLoaded', function() {
    const addDeviceBtn = document.getElementById('addDeviceBtn');
    if (addDeviceBtn) {
        console.log("Configurando botón para añadir dispositivos"); // Debug
        
        addDeviceBtn.addEventListener('click', function() {
            const deviceId = document.getElementById('addDeviceSelect')?.value;
            const playlistId = currentPlaylistId;
            
            if (!deviceId) {
                alert('Por favor, selecciona un dispositivo para asignar a la lista');
                return;
            }
            
            if (!playlistId) {
                alert('Error: No se pudo identificar la lista de reproducción');
                return;
            }
            
            addDeviceToPlaylist(playlistId, deviceId);
        });
    }
});

// Añadir debug para verificar que se está cargando esta parte
console.log("Código de gestión de asignaciones dispositivo-playlist cargado correctamente");

// Modificar la función openPlaylistDetail para incluir la carga de dispositivos
async function openPlaylistDetail(playlistId) {
    currentPlaylistId = playlistId;
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}`);
        if (!response.ok) throw new Error('Error al cargar detalles de la playlist');
        
        const playlist = await response.json();
        
        // Código existente para mostrar información de la playlist
        document.getElementById('playlistDetailTitle').textContent = playlist.title;
        document.getElementById('playlistDetailDescription').textContent = playlist.description || 'Sin descripción';
        document.getElementById('playlistDetailDate').textContent = `Creada: ${formatDate(playlist.creation_date)}`;
        
        // Fecha de expiración
        const expirationBadge = document.getElementById('playlistDetailExpirationDate');
        if (playlist.expiration_date) {
            const expired = isExpired(playlist.expiration_date);
            expirationBadge.className = `badge ${expired ? 'bg-danger' : 'bg-info'}`;
            expirationBadge.textContent = `${expired ? 'Expiró' : 'Expira'}: ${formatDate(playlist.expiration_date)}`;
        } else {
            expirationBadge.className = 'badge bg-secondary';
            expirationBadge.textContent = 'Sin fecha de expiración';
        }

        // Estado de la playlist
        const statusBadge = document.getElementById('playlistDetailStatus');
        const isActive = isPlaylistActive(playlist);
        statusBadge.className = `badge ${isActive ? 'bg-success' : 'bg-danger'}`;
        statusBadge.textContent = isActive ? 'Activa' : 'Inactiva';
        
        document.getElementById('playlistDownloadBtn').onclick = () => {
            window.location.href = `${API_URL}/playlists/${playlistId}/download`;
        };
        
        // Configurar botón de editar
        document.getElementById('editPlaylistBtn').onclick = () => {
            preparePlaylistForEditing(playlist);
        };
        // Configurar botón para eliminar playlist
        document.getElementById('deletePlaylistBtn').onclick = () => {
            if (confirm('¿Estás seguro de que deseas eliminar esta lista de reproducción?')) {
                deletePlaylist(playlistId);
            }
        };
        // Mostrar videos en la playlist
        const playlistVideos = document.getElementById('playlistVideos');
        playlistVideos.innerHTML = '';
        
        if (playlist.videos.length === 0) {
            playlistVideos.innerHTML = '<p class="text-center">No hay videos en esta lista</p>';
        } else {
            playlist.videos.forEach(video => {
                const videoExpired = video.expiration_date && isExpired(video.expiration_date);
                const videoItem = document.createElement('div');
                videoItem.className = `list-group-item list-group-item-action d-flex justify-content-between align-items-center ${videoExpired ? 'list-group-item-danger' : ''}`;
                videoItem.innerHTML = `
                    <div>
                        <h6 class="mb-1">${video.title}</h6>
                        <small>${video.description || 'Sin descripción'}</small>
                        ${video.expiration_date ? 
                            `<div>
                                <span class="badge ${videoExpired ? 'bg-danger' : 'bg-info'}">
                                    ${videoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                                </span>
                            </div>` : ''}
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeVideoFromPlaylist(${playlistId}, ${video.id})">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                playlistVideos.appendChild(videoItem);
            });
        }
        
        // Cargar videos disponibles para agregar (solo los no expirados)
        const addVideoSelect = document.getElementById('addVideoSelect');
        addVideoSelect.innerHTML = '<option value="">Seleccionar video...</option>';
        
        // Filtrar videos que no están en la playlist y que no han expirado
        const playlistVideoIds = new Set(playlist.videos.map(v => v.id));
        const availableVideos = allVideos.filter(video => 
            !playlistVideoIds.has(video.id) && 
            (!video.expiration_date || !isExpired(video.expiration_date))
        );
        
        if (availableVideos.length === 0) {
            addVideoSelect.innerHTML += '<option disabled>No hay videos disponibles para agregar</option>';
        } else {
            availableVideos.forEach(video => {
                const option = document.createElement('option');
                option.value = video.id;
                option.textContent = video.title;
                addVideoSelect.appendChild(option);
            });
        }
        
        // Configurar botón para agregar video
        document.getElementById('addVideoBtn').onclick = () => {
            const videoId = addVideoSelect.value;
            if (videoId) {
                addVideoToPlaylist(playlistId, parseInt(videoId));
            } else {
                alert('Por favor, selecciona un video para agregar a la lista');
            }
        };
        
        // ... (resto del código existente)
        
        // Cargar dispositivos asignados a la playlist
        await loadPlaylistDevices(playlistId);
        
        // Cargar dispositivos disponibles para asignar
        await loadAvailableDevices(playlistId);
        
        // Configurar botón para agregar dispositivo
        document.getElementById('addDeviceBtn').onclick = () => {
            const deviceId = document.getElementById('addDeviceSelect').value;
            if (deviceId) {
                addDeviceToPlaylist(playlistId, deviceId);
            } else {
                alert('Por favor, selecciona un dispositivo para asignar a la lista');
            }
        };
        
        // Mostrar el modal
        const modal = new bootstrap.Modal(document.getElementById('playlistDetailModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error al cargar detalles de la playlist:', error);
        alert(`Error al cargar los detalles de la lista de reproducción: ${error.message}`);
    }
}

 // Asignar playlist a dispositivo
async function assignPlaylistToDevice(playlistId) {
    try {
        const response = await fetch('/api/device-playlists/', {
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
            const errorData = await response.json();
            throw new Error(errorData.detail || `Error al asignar la playlist: ${response.status}`);
        }
        
        // Mostrar mensaje de éxito
        const alertBox = document.createElement('div');
        alertBox.className = 'alert alert-success alert-dismissible fade show mt-3';
        alertBox.innerHTML = `
            <strong>¡Éxito!</strong> La lista de reproducción ha sido asignada al dispositivo.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insertar el mensaje en la página
        const modalElement = document.getElementById('assignPlaylistModal');
        const modal = bootstrap.Modal.getInstance(modalElement);
        modal.hide();
        
        const cardBody = document.querySelector('.card-body');
        cardBody.insertBefore(alertBox, cardBody.firstChild);
        
        // Recargar la lista de playlists asignadas
        await loadAssignedPlaylists();
        
    } catch (error) {
        console.error('Error al asignar playlist:', error);
        alert(`Error al asignar la lista de reproducción: ${error.message}`);
    }
}

// Eliminar asignación de playlist a dispositivo
async function removePlaylistFromDevice(deviceId, playlistId) {
    try {
        if (!confirm('¿Está seguro que desea eliminar esta asignación? La lista de reproducción ya no se reproducirá en este dispositivo.')) {
            return;
        }
        
        const response = await fetch(`/api/device-playlists/${deviceId}/${playlistId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Error al eliminar la asignación: ${response.status}`);
        }
        
        // Mostrar mensaje de éxito
        const alertBox = document.createElement('div');
        alertBox.className = 'alert alert-success alert-dismissible fade show mt-3';
        alertBox.innerHTML = `
            <strong>¡Éxito!</strong> La lista de reproducción ha sido desasignada del dispositivo.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insertar el mensaje en la página
        const cardBody = document.querySelector('.card-body');
        cardBody.insertBefore(alertBox, cardBody.firstChild);
        
        // Recargar la lista de playlists asignadas
        await loadAssignedPlaylists();
        // También recargar las playlists disponibles para el modal
        await loadAvailablePlaylists();
        
    } catch (error) {
        console.error('Error al eliminar asignación de playlist:', error);
        alert(`Error al eliminar la asignación: ${error.message}`);
    }
}

// Abrir modal con detalles de playlist
function openPlaylistDetails(playlistId) {
    // Redirigir a la pestaña de playlists y mostrar los detalles de la playlist seleccionada
    window.location.href = `/ui/playlists/#${playlistId}`;
}

// Inicializar componentes
if (refreshPlaylistsBtn) {
    refreshPlaylistsBtn.addEventListener('click', loadAssignedPlaylists);
}

if (showOnlyActivePlaylistsCheck) {
    showOnlyActivePlaylistsCheck.addEventListener('change', loadAvailablePlaylists);
}

if (confirmAssignPlaylistBtn) {
    confirmAssignPlaylistBtn.addEventListener('click', () => {
        const playlistId = availablePlaylistsSelect.value;
        if (!playlistId) {
            alert('Por favor, seleccione una lista de reproducción para asignar');
            return;
        }
        assignPlaylistToDevice(playlistId);
    });
}

// Exponer la función para que pueda ser llamada desde HTML
window.removePlaylistFromDevice = removePlaylistFromDevice;

// Cargar datos iniciales
loadAssignedPlaylists();
loadAvailablePlaylists();


// Llamar a la inicialización cuando se carga el documento
document.addEventListener('DOMContentLoaded', function() {
// Todas las inicializaciones existentes...

// Inicializar la gestión de playlists
initPlaylistManagement();
});