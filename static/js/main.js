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
async function openPlaylistDetail(playlistId) {
    currentPlaylistId = playlistId;
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}`);
        if (!response.ok) throw new Error('Error al cargar detalles de la playlist');
        
        const playlist = await response.json();
        
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
        
        // Mostrar el modal
        const modal = new bootstrap.Modal(document.getElementById('playlistDetailModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error al cargar detalles de la playlist:', error);
        alert(`Error al cargar los detalles de la lista de reproducción: ${error.message}`);
    }
}

// Preparar playlist para edición
function preparePlaylistForEditing(playlist) {
    document.getElementById('editPlaylistId').value = playlist.id;
    document.getElementById('editPlaylistTitle').value = playlist.title;
    document.getElementById('editPlaylistDescription').value = playlist.description || '';
    
    // Formatear fecha para el input datetime-local
    if (playlist.expiration_date) {
        const date = new Date(playlist.expiration_date);
        // Asegurarse de que la zona horaria se maneje correctamente
        const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
            .toISOString()
            .slice(0, 16);
        document.getElementById('editPlaylistExpiration').value = localDatetime;
    } else {
        document.getElementById('editPlaylistExpiration').value = '';
    }
    
    document.getElementById('editPlaylistActive').checked = playlist.is_active;
    
    // Cerrar modal de detalles y abrir modal de edición
    bootstrap.Modal.getInstance(document.getElementById('playlistDetailModal')).hide();
    const editModal = new bootstrap.Modal(document.getElementById('editPlaylistModal'));
    editModal.show();
}

// Editar video
async function editVideo(videoId) {
    try {
        const video = allVideos.find(v => v.id === videoId);
        if (!video) throw new Error('Video no encontrado');
        
        document.getElementById('editVideoId').value = video.id;
        document.getElementById('editVideoTitle').value = video.title;
        document.getElementById('editVideoDescription').value = video.description || '';
        
        // Formatear fecha para el input datetime-local
        if (video.expiration_date) {
            const date = new Date(video.expiration_date);
            const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                .toISOString()
                .slice(0, 16);
            document.getElementById('editVideoExpiration').value = localDatetime;
        } else {
            document.getElementById('editVideoExpiration').value = '';
        }
        
        const editModal = new bootstrap.Modal(document.getElementById('editVideoModal'));
        editModal.show();
        
    } catch (error) {
        console.error('Error al preparar el video para edición:', error);
        alert(`Error: ${error.message}`);
    }
}

// Guardar cambios de la playlist
async function savePlaylistChanges() {
    try {
        const playlistId = document.getElementById('editPlaylistId').value;
        
        // Obtener los valores de los campos del formulario
        const playlistData = {
            title: document.getElementById('editPlaylistTitle').value,
            description: document.getElementById('editPlaylistDescription').value || null,
            expiration_date: document.getElementById('editPlaylistExpiration').value || null,
            is_active: document.getElementById('editPlaylistActive').checked
        };
        
        console.log("Enviando datos:", playlistData); // Para depuración
        
        const response = await fetch(`${API_URL}/playlists/${playlistId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(playlistData),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al actualizar la lista');
        }
        
        alert('Lista de reproducción actualizada correctamente');
        bootstrap.Modal.getInstance(document.getElementById('editPlaylistModal')).hide();
        
        // Recargar playlists y abrir detalles
        await loadPlaylists();
        await openPlaylistDetail(parseInt(playlistId)); // Asegurarse de esperar a que termine
        
    } catch (error) {
        console.error('Error al guardar cambios de la playlist:', error);
        alert(`Error: ${error.message}`);
    }
}

// Guardar cambios del video
async function saveVideoChanges() {
    try {
        const videoId = document.getElementById('editVideoId').value;
        
        const videoData = {
            title: document.getElementById('editVideoTitle').value,
            description: document.getElementById('editVideoDescription').value || null,
            expiration_date: document.getElementById('editVideoExpiration').value || null
        };
        
        const response = await fetch(`${API_URL}/videos/${videoId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(videoData),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al actualizar el video');
        }
        
        alert('Video actualizado correctamente');
        bootstrap.Modal.getInstance(document.getElementById('editVideoModal')).hide();
        
        // Recargar videos
        await loadVideos();
        
    } catch (error) {
        console.error('Error al guardar cambios del video:', error);
        alert(`Error: ${error.message}`);
    }
}

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
async function loadPlaylistDevices(playlistId) {
    try {
        const response = await fetch(`${API_URL}/device-playlists/playlist/${playlistId}/devices`);
        if (!response.ok) throw new Error('Error al cargar dispositivos asignados');
        
        const assignedDevices = await response.json();
        
        // Obtener el contenedor de dispositivos
        const playlistDevices = document.getElementById('playlistDevices');
        if (!playlistDevices) return;
        
        // Limpiar contenido actual
        const devicesContainer = document.getElementById('assignedDevicesContainer');
        if (devicesContainer) {
            if (assignedDevices.length === 0) {
                devicesContainer.innerHTML = '<p class="text-center">No hay dispositivos asignados a esta lista</p>';
                return;
            }
            
            // Crear la lista de dispositivos asignados
            const devicesList = document.createElement('div');
            devicesList.className = 'list-group';
            
            assignedDevices.forEach(device => {
                const deviceItem = document.createElement('div');
                deviceItem.className = `list-group-item list-group-item-action d-flex justify-content-between align-items-center ${device.is_active ? '' : 'list-group-item-warning'}`;
                deviceItem.innerHTML = `
                    <div>
                        <h6 class="mb-1">${device.name} (${device.device_id})</h6>
                        <small>${device.location || ''} ${device.tienda ? ' - ' + device.tienda : ''}</small>
                        <div>
                            <span class="badge ${device.is_active ? 'bg-success' : 'bg-danger'}">
                                ${device.is_active ? 'Activo' : 'Inactivo'}
                            </span>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeDeviceFromPlaylist('${device.device_id}', ${playlistId})">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                devicesList.appendChild(deviceItem);
            });
            
            devicesContainer.innerHTML = '';
            devicesContainer.appendChild(devicesList);
        }
    } catch (error) {
        console.error('Error al cargar dispositivos asignados:', error);
        const devicesContainer = document.getElementById('assignedDevicesContainer');
        if (devicesContainer) {
            devicesContainer.innerHTML = `<div class="alert alert-danger">Error al cargar dispositivos: ${error.message}</div>`;
        }
    }
}


// Función para cargar dispositivos disponibles para asignar
async function loadAvailableDevices(playlistId) {
    try {
        // Obtener todos los dispositivos
        const allDevicesResponse = await fetch(`${API_URL}/devices/?active_only=true`);
        if (!allDevicesResponse.ok) throw new Error('Error al cargar dispositivos');
        const allDevices = await allDevicesResponse.json();
        
        // Obtener dispositivos ya asignados
        const assignedDevicesResponse = await fetch(`${API_URL}/device-playlists/playlist/${playlistId}/devices`);
        if (!assignedDevicesResponse.ok) throw new Error('Error al cargar dispositivos asignados');
        const assignedDevices = await assignedDevicesResponse.json();
        
        // Filtrar dispositivos que no están asignados
        const assignedDeviceIds = new Set(assignedDevices.map(d => d.device_id));
        const availableDevices = allDevices.filter(device => !assignedDeviceIds.has(device.device_id));
        
        // Actualizar el select de dispositivos disponibles
        const addDeviceSelect = document.getElementById('addDeviceSelect');
        if (!addDeviceSelect) return;
        
        addDeviceSelect.innerHTML = '<option value="">Seleccionar dispositivo...</option>';
        
        if (availableDevices.length === 0) {
            addDeviceSelect.innerHTML += '<option disabled>No hay dispositivos disponibles para asignar</option>';
        } else {
            availableDevices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.device_id;
                option.textContent = `${device.name} (${device.device_id})`;
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
addDeviceToPlaylist

// Función para eliminar un dispositivo de una playlist
async function removeDeviceFromPlaylist(deviceId, playlistId) {
    try {
        const response = await fetch(`${API_URL}/device-playlists/${deviceId}/${playlistId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al eliminar la asignación');
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