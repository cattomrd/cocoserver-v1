// Configuración global
const API_URL = '/api';
let allVideos = [];
let allPlaylists = [];
let currentPlaylistId = null;

// Función para comprobar si un elemento existe antes de acceder a él
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

// Verificar si una fecha ha expirado
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

// Formatear fecha para mostrar
function formatDate(dateString) {
    if (!dateString) return 'Sin fecha';
    
    try {
        const date = new Date(dateString);
        // Verificar si la fecha es válida
        if (isNaN(date.getTime())) {
            return 'Fecha inválida';
        }
        return date.toLocaleString();
    } catch (e) {
        console.error("Error al formatear fecha:", e);
        return 'Error de formato';
    }
}

// Verificar si una playlist está activa
function isPlaylistActive(playlist) {
    if (!playlist) return false;
    if (playlist.is_active === false) return false;
    
    const now = new Date();
    
    // Verificar fecha de inicio
    if (playlist.start_date && new Date(playlist.start_date) > now) return false;
    
    // Verificar fecha de expiración
    if (playlist.expiration_date && isExpired(playlist.expiration_date)) return false;
    
    return true;
}

// Función para obtener el estado de una playlist considerando las fechas
function getPlaylistStatus(playlist) {
    const now = new Date();
    
    if (!playlist.is_active) {
        return { status: 'inactive', text: 'Inactiva', class: 'bg-secondary' };
    }
    
    // Verificar si está programada para el futuro
    if (playlist.start_date && new Date(playlist.start_date) > now) {
        return { 
            status: 'scheduled', 
            text: `Programada (inicia: ${formatDate(playlist.start_date)})`, 
            class: 'bg-warning' 
        };
    }
    
    // Verificar si ha expirado
    if (playlist.expiration_date && isExpired(playlist.expiration_date)) {
        return { status: 'expired', text: 'Expirada', class: 'bg-danger' };
    }
    
    // Está activa y en período válido
    return { status: 'active', text: 'Activa', class: 'bg-success' };
}

// Función para formatear el período de actividad de una playlist
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



// Mostrar notificación
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

// Función para probar la conexión a la API
async function testApiConnection() {
    try {
        console.log("Probando conexión a API:", `${API_URL}/videos/`);
        const response = await fetch(`${API_URL}/videos/`);
        
        if (!response.ok) {
            console.error("La API no responde correctamente:", response.status, response.statusText);
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

// ----- GESTIÓN DE VIDEOS -----

// Cargar videos desde la API
async function loadVideos(filter = 'all') {
    console.log("Cargando videos con filtro:", filter);
    
    // Obtener el contenedor de la tabla de manera segura
    const videosList = document.getElementById('videosList');
    if (!videosList) {
        console.error("Elemento videosList no encontrado");
        return;
    }
    
    try {
        // Mostrar estado de carga
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
        
        console.log("Solicitando videos desde:", `${API_URL}/videos/`);
        
        // Realizar petición a la API
        const response = await fetch(`${API_URL}/videos/`);
        console.log("Respuesta de la API:", response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }
        
        // Procesar respuesta
        const responseData = await response.json();
        console.log("Datos recibidos:", responseData);
        
        // Guardar los videos
        allVideos = Array.isArray(responseData) ? responseData : [];
        
        if (!Array.isArray(allVideos)) {
            throw new Error("Formato de datos inválido");
        }
        
        // Filtrar videos según el criterio seleccionado
        let filteredVideos = allVideos;
        if (filter === 'active') {
            filteredVideos = allVideos.filter(video => !video.expiration_date || !isExpired(video.expiration_date));
        } else if (filter === 'expired') {
            filteredVideos = allVideos.filter(video => video.expiration_date && isExpired(video.expiration_date));
        }
        
        // Actualizar contador de videos de manera segura
        safeElementOperation('videoCountBadge', element => {
            element.textContent = `${filteredVideos.length} videos`;
        });
        
        // Limpiar la lista de videos
        let videosHTML = '';
        
        // Mostrar mensaje si no hay videos
        if (filteredVideos.length === 0) {
            videosHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <p>No hay videos disponibles. ¡Sube tu primer video!</p>
                    </td>
                </tr>
            `;
        } else {
            // Generar HTML para cada video como fila de tabla
            filteredVideos.forEach(video => {
                const isVideoExpired = video.expiration_date && isExpired(video.expiration_date);
                
                videosHTML += `
                    <tr class="${isVideoExpired ? 'table-danger' : ''}">
                        <td>${video.title || ''}</td>
                        <td>${video.description || '<span class="text-muted">Sin descripción</span>'}</td>
                        <td>${formatDate(video.upload_date)}</td>
                        <td>
                            ${video.expiration_date ? 
                                `<span class="badge ${isVideoExpired ? 'bg-danger' : 'bg-info'}">
                                    ${isVideoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                                </span>` : 
                                '<span class="text-muted">Sin expiración</span>'}
                        </td>
                        <td>
                            <span class="badge ${isVideoExpired ? 'bg-danger' : 'bg-success'}">
                                ${isVideoExpired ? 'Expirado' : 'Activo'}
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
            });
        }
        
        // Insertar todas las filas de videos
        videosList.innerHTML = videosHTML;
        
    } catch (error) {
        console.error('Error al cargar videos:', error);
        
        // Mostrar mensaje de error en la tabla de manera segura
        if (videosList) {
            videosList.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div class="alert alert-danger">Error al cargar videos: ${error.message}</div>
                    </td>
                </tr>
            `;
        }
        
        // Mostrar notificación
        showToast(`Error al cargar videos: ${error.message}`, 'error');
    }
}

// Filtrar videos por título
function filterVideosByTitle(searchText) {
    console.log("Filtrando videos por texto:", searchText);
    
    // Normalizar texto de búsqueda
    searchText = (searchText || '').toLowerCase().trim();
    
    // Obtener contenedor de manera segura
    const videosList = document.getElementById('videosList');
    if (!videosList) {
        console.error("Elemento videosList no encontrado");
        return;
    }
    
    try {
        // Si no hay texto de búsqueda, mostrar todos los videos
        if (!searchText) {
            const filterSelect = document.getElementById('videoFilterExpiration');
            const currentFilter = filterSelect ? filterSelect.value : 'all';
            loadVideos(currentFilter);
            return;
        }
        
        // Filtrar videos
        const filteredVideos = allVideos.filter(video => 
            (video.title && video.title.toLowerCase().includes(searchText)) ||
            (video.description && video.description.toLowerCase().includes(searchText))
        );
        
        // Actualizar contador de manera segura
        safeElementOperation('videoCountBadge', element => {
            element.textContent = `${filteredVideos.length} videos`;
        });
        
        // Generar HTML para resultados
        let videosHTML = '';
        
        if (filteredVideos.length === 0) {
            videosHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <p>No se encontraron videos con esos criterios de búsqueda.</p>
                    </td>
                </tr>
            `;
        } else {
            // Añadir cada video como fila de la tabla
            filteredVideos.forEach(video => {
                const isVideoExpired = video.expiration_date && isExpired(video.expiration_date);
                
                videosHTML += `
                    <tr class="${isVideoExpired ? 'table-danger' : ''}">
                        <td>${video.title || ''}</td>
                        <td>${video.description || '<span class="text-muted">Sin descripción</span>'}</td>
                        <td>${formatDate(video.upload_date)}</td>
                        <td>
                            ${video.expiration_date ? 
                                `<span class="badge ${isVideoExpired ? 'bg-danger' : 'bg-info'}">
                                    ${isVideoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                                </span>` : 
                                '<span class="text-muted">Sin expiración</span>'}
                        </td>
                        <td>
                            <span class="badge ${isVideoExpired ? 'bg-danger' : 'bg-success'}">
                                ${isVideoExpired ? 'Expirado' : 'Activo'}
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
            });
        }
        
        // Actualizar el contenido de la tabla
        videosList.innerHTML = videosHTML;
        
    } catch (error) {
        console.error('Error al filtrar videos:', error);
        
        // Mostrar mensaje de error en la tabla
        if (videosList) {
            videosList.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div class="alert alert-danger">Error al filtrar videos: ${error.message}</div>
                    </td>
                </tr>
            `;
        }
        
        showToast(`Error al filtrar videos: ${error.message}`, 'error');
    }
}

// Subir un video
async function uploadVideo(formData) {
    // Acceder al elemento de progreso de manera segura
    const progressBar = document.querySelector('#uploadProgress .progress-bar');
    const progressContainer = document.getElementById('uploadProgress');
    
    // Mostrar la barra de progreso si existe
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
                    
                    // Resetear el formulario de manera segura
                    safeElementOperation('videoUploadForm', form => {
                        form.reset();
                    });
                    
                    // Cerrar el formulario de subida de manera segura
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
                    
                    // Recargar los videos
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
                
                // Ocultar la barra de progreso después de terminar
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
        
        // Ocultar la barra de progreso en caso de error
        if (progressContainer) {
            progressContainer.classList.add('d-none');
        }
    }
}

// Editar un video
async function editVideo(videoId) {
    console.log("Editando video:", videoId);
    
    try {
        // Buscar el video en los datos cargados
        const video = allVideos.find(v => v.id === videoId);
        if (!video) {
            throw new Error('Video no encontrado en los datos cargados');
        }
        
        console.log("Datos del video a editar:", video);
        
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
        
        // Mostrar el modal de edición de manera segura
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

// Guardar cambios de un video
async function saveVideoChanges() {
    console.log("Guardando cambios de video...");
    
    try {
        // Obtener datos del formulario de manera segura
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
        
        console.log(`Actualizando video ID ${videoId} con título "${title}"`);
        
        // Enviar datos a la API
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
            } catch (e) {
                // Si no es JSON, ignorar
            }
            
            throw new Error(errorMessage);
        }
        
        // Actualización exitosa
        console.log("Video actualizado correctamente");
        
        // Cerrar el modal de manera segura
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
        
        // Cargar videos con un retardo para asegurar que todos los eventos relacionados con la actualización se han completado
        setTimeout(() => {
            loadVideos();
        }, 500);
        
    } catch (error) {
        console.error('Error al guardar cambios del video:', error);
        showToast(`Error al guardar cambios: ${error.message}`, 'error');
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
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al eliminar el video');
        }
        
        showToast('Video eliminado correctamente', 'success');
        
        // Recargar videos
        setTimeout(() => {
            loadVideos();
        }, 500);
        
    } catch (error) {
        console.error('Error al eliminar video:', error);
        showToast(`Error al eliminar el video: ${error.message}`, 'error');
    }
}

// ----- GESTIÓN DE PLAYLISTS -----

// Actualizar la función loadPlaylists para mostrar información de fechas
async function loadPlaylists(filter = 'all') {
    console.log("Cargando playlists con filtro:", filter);
    
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
        safeElementOperation('playlistCountBadge', element => {
            element.textContent = `${filteredPlaylists.length} listas`;
        });
        
        // Generar HTML para las playlists
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
            // Generar HTML para cada playlist
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
        
        // Insertar todas las filas de playlists
        playlistsList.innerHTML = playlistsHTML;
        
    } catch (error) {
        console.error('Error al cargar playlists:', error);
        
        // Mostrar mensaje de error
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

// Filtrar playlists por título o descripción
function filterPlaylistsByTitle(searchText) {
    console.log("Filtrando playlists por texto:", searchText);
    
    // Normalizar texto de búsqueda
    searchText = (searchText || '').toLowerCase().trim();
    
    // Obtener contenedor de manera segura
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
        
        // Actualizar contador de manera segura
        safeElementOperation('playlistCountBadge', element => {
            element.textContent = `${filteredPlaylists.length} listas`;
        });
        
        // Generar HTML para las playlists
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
            // Generar HTML para cada playlist
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
        
        // Actualizar el contenido de la tabla
        playlistsList.innerHTML = playlistsHTML;
        
    } catch (error) {
        console.error('Error al filtrar playlists:', error);
        
        // Mostrar mensaje de error
        if (playlistsList) {
            playlistsList.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div class="alert alert-danger">Error al filtrar listas: ${error.message}</div>
                    </td>
                </tr>
            `;
        }
        
        showToast(`Error al filtrar listas: ${error.message}`, 'error');
    }
}

// Crear una playlist con fecha de inicio
async function createPlaylist(playlistData) {
    try {
        // Obtener datos del formulario incluyendo fecha de inicio
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
        
        // Resetear el formulario
        safeElementOperation('playlistCreateForm', form => {
            form.reset();
        });
        
        // Cerrar el formulario
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
        
        // Recargar playlists
        setTimeout(() => {
            loadPlaylists();
        }, 500);
        
    } catch (error) {
        console.error('Error al crear playlist:', error);
        showToast(`Error al crear la lista de reproducción: ${error.message}`, 'error');
    }
}

// Preparar playlist para edición incluyendo fecha de inicio
function preparePlaylistForEditing(playlist) {
    console.log("Preparando playlist para edición:", playlist);
    
    try {
        // Verificar que existan los elementos necesarios
        const editIdInput = document.getElementById('editPlaylistId');
        const editTitleInput = document.getElementById('editPlaylistTitle');
        const editDescriptionInput = document.getElementById('editPlaylistDescription');
        const editStartDateInput = document.getElementById('editPlaylistStartDate');
        const editExpirationInput = document.getElementById('editPlaylistExpiration');
        const editActiveCheckbox = document.getElementById('editPlaylistActive');
        
        if (!editIdInput || !editTitleInput || !editDescriptionInput || !editExpirationInput || !editActiveCheckbox) {
            throw new Error('No se encontraron todos los campos del formulario de edición');
        }
        
        // Asignar valores a los campos
        editIdInput.value = playlist.id;
        editTitleInput.value = playlist.title || '';
        editDescriptionInput.value = playlist.description || '';
        
        // Formatear fecha de inicio para el input datetime-local
        if (playlist.start_date && editStartDateInput) {
            try {
                const date = new Date(playlist.start_date);
                const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                    .toISOString()
                    .slice(0, 16);
                editStartDateInput.value = localDatetime;
            } catch (e) {
                console.error("Error al procesar fecha de inicio:", e);
                editStartDateInput.value = '';
            }
        } else if (editStartDateInput) {
            editStartDateInput.value = '';
        }
        
        // Formatear fecha de expiración para el input datetime-local
        if (playlist.expiration_date) {
            try {
                const date = new Date(playlist.expiration_date);
                const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                    .toISOString()
                    .slice(0, 16);
                editExpirationInput.value = localDatetime;
            } catch (e) {
                console.error("Error al procesar fecha de expiración:", e);
                editExpirationInput.value = '';
            }
        } else {
            editExpirationInput.value = '';
        }
        
        editActiveCheckbox.checked = playlist.is_active || false;
        
        // Manejar modales
        const detailModal = document.getElementById('playlistDetailModal');
        const editModal = document.getElementById('editPlaylistModal');
        
        if (!detailModal || !editModal) {
            throw new Error("No se encontraron los modales necesarios");
        }
        
        // Cerrar modal de detalles
        if (window.bootstrap) {
            try {
                const detailModalInstance = bootstrap.Modal.getInstance(detailModal);
                if (detailModalInstance) {
                    detailModalInstance.hide();
                }
            } catch (e) {
                console.error("Error al cerrar modal de detalles:", e);
            }
        }
        
        // Mostrar modal de edición
        setTimeout(() => {
            if (window.bootstrap) {
                try {
                    const editModalInstance = new bootstrap.Modal(editModal);
                    editModalInstance.show();
                } catch (e) {
                    console.error("Error al mostrar modal de edición:", e);
                    showToast("Error al abrir el formulario de edición", 'error');
                }
            }
        }, 500);
    } catch (error) {
        console.error("Error al preparar playlist para edición:", error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Cargar videos disponibles para una playlist
async function loadAvailableVideos(playlistId, playlist) {
    // Obtener el select de manera segura
    const addVideoSelect = document.getElementById('addVideoSelect');
    if (!addVideoSelect) {
        console.error("No se encontró el select para añadir videos");
        return;
    }
    
    try {
        // Inicializar el select
        addVideoSelect.innerHTML = '<option value="">Seleccionar video...</option>';
        
        // Asegurarnos de que allVideos esté disponible
        if (!allVideos || allVideos.length === 0) {
            try {
                const response = await fetch(`${API_URL}/videos/`);
                if (response.ok) {
                    allVideos = await response.json();
                } else {
                    throw new Error(`Error al cargar videos: ${response.status} ${response.statusText}`);
                }
            } catch (err) {
                console.error("Error al cargar videos:", err);
                addVideoSelect.innerHTML += '<option disabled>Error al cargar videos disponibles</option>';
                return;
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

// Cargar los dispositivos asignados a una playlist
async function loadPlaylistDevices(playlistId) {
    console.log("Cargando dispositivos para playlist:", playlistId);

    // Obtener el contenedor de manera segura
    const devicesContainer = document.getElementById('assignedDevicesContainer');
    if (!devicesContainer) {
        console.error("No se encontró el contenedor de dispositivos asignados");
        return;
    }
    
    try {
        // Mostrar indicador de carga
        devicesContainer.innerHTML = `
            <div class="text-center">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <span class="ms-2">Cargando dispositivos asignados...</span>
            </div>
        `;

        // Realizar la petición a la API para obtener los dispositivos asignados
        const response = await fetch(`${API_URL}/device-playlists/playlist/${playlistId}/devices`);
        
        if (!response.ok) {
            throw new Error(`Error al cargar dispositivos asignados: ${response.status} ${response.statusText}`);
        }
        
        const assignedDevices = await response.json();
        console.log("Dispositivos asignados recibidos:", assignedDevices);
        
        // Mostrar mensaje si no hay dispositivos asignados
        if (!assignedDevices || assignedDevices.length === 0) {
            devicesContainer.innerHTML = '<p class="text-center">No hay dispositivos asignados a esta lista</p>';
            return;
        }
        
        // Crear HTML para la tabla de dispositivos
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
        
        // Actualizar el contenedor con la tabla
        devicesContainer.innerHTML = tableHTML;
        
    } catch (error) {
        console.error('Error al cargar dispositivos asignados:', error);
        devicesContainer.innerHTML = `<div class="alert alert-danger">Error al cargar dispositivos: ${error.message}</div>`;
    }
}

// Cargar dispositivos disponibles para asignar
async function loadAvailableDevices(playlistId) {
    console.log("Cargando dispositivos disponibles para playlist:", playlistId);
    
    try {
        // Obtener todos los dispositivos activos
        const allDevicesResponse = await fetch(`${API_URL}/devices/?active_only=true`);
        if (!allDevicesResponse.ok) {
            throw new Error(`Error al cargar dispositivos: ${allDevicesResponse.status} ${allDevicesResponse.statusText}`);
        }
        const allDevices = await allDevicesResponse.json();
        console.log("Todos los dispositivos:", allDevices);
        
        // Obtener dispositivos ya asignados
        const assignedDevicesResponse = await fetch(`${API_URL}/device-playlists/playlist/${playlistId}/devices`);
        if (!assignedDevicesResponse.ok) {
            throw new Error(`Error al cargar dispositivos asignados: ${assignedDevicesResponse.status} ${assignedDevicesResponse.statusText}`);
        }
        const assignedDevices = await assignedDevicesResponse.json();
        console.log("Dispositivos ya asignados:", assignedDevices);
        
        // Filtrar dispositivos que no están asignados
        const assignedDeviceIds = new Set(assignedDevices.map(d => d.device_id));
        const availableDevices = allDevices.filter(device => !assignedDeviceIds.has(device.device_id));
        console.log("Dispositivos disponibles para asignar:", availableDevices);
        
        // Actualizar el select de dispositivos disponibles de manera segura
        safeElementOperation('addDeviceSelect', element => {
            // Limpiar y añadir opción por defecto
            element.innerHTML = '<option value="">Seleccionar dispositivo...</option>';
            
            if (availableDevices.length === 0) {
                element.innerHTML += '<option disabled>No hay dispositivos disponibles para asignar</option>';
            } else {
                // Añadir cada dispositivo disponible
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

// Agregar video a playlist
async function addVideoToPlaylist(playlistId, videoId) {
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}/videos/${videoId}`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al añadir el video');
        }
        
        showToast('Video añadido a la lista correctamente', 'success');
        
        // Recargar detalles
        setTimeout(() => {
            openPlaylistDetail(playlistId);
        }, 500);
        
    } catch (error) {
        console.error('Error al añadir video a playlist:', error);
        showToast(`Error al añadir el video a la lista: ${error.message}`, 'error');
    }
}

// Eliminar video de playlist
async function removeVideoFromPlaylist(playlistId, videoId) {
    if (!confirm('¿Estás seguro de que deseas eliminar este video de la lista de reproducción?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/playlists/${playlistId}/videos/${videoId}`, {
            method: 'DELETE',
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al eliminar el video');
        }
        
        showToast('Video eliminado de la lista correctamente', 'success');
        
        // Recargar detalles
        setTimeout(() => {
            openPlaylistDetail(playlistId);
        }, 500);
        
    } catch (error) {
        console.error('Error al eliminar video de playlist:', error);
        showToast(`Error al eliminar el video de la lista: ${error.message}`, 'error');
    }
}

// Asignar un dispositivo a una playlist
async function addDeviceToPlaylist(playlistId, deviceId) {
    try {
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
        
        // Éxito - mostrar mensaje y recargar los dispositivos asignados
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

// Eliminar un dispositivo de una playlist
async function removeDeviceFromPlaylist(deviceId, playlistId) {
    console.log(`Eliminando dispositivo ${deviceId} de playlist ${playlistId}`);
    
    try {
        // Verificar que tenemos los datos necesarios
        if (!playlistId || !deviceId) {
            throw new Error("Faltan datos para la eliminación");
        }
        
        // Enviar la petición a la API
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
}

// Preparar playlist para edición
function preparePlaylistForEditing(playlist) {
    console.log("Preparando playlist para edición:", playlist);
    
    try {
        // Verificar que existan los elementos necesarios
        const editIdInput = document.getElementById('editPlaylistId');
        const editTitleInput = document.getElementById('editPlaylistTitle');
        const editDescriptionInput = document.getElementById('editPlaylistDescription');
        const editExpirationInput = document.getElementById('editPlaylistExpiration');
        const editActiveCheckbox = document.getElementById('editPlaylistActive');
        
        if (!editIdInput || !editTitleInput || !editDescriptionInput || !editExpirationInput || !editActiveCheckbox) {
            throw new Error('No se encontraron todos los campos del formulario de edición');
        }
        
        // Asignar valores a los campos
        editIdInput.value = playlist.id;
        editTitleInput.value = playlist.title || '';
        editDescriptionInput.value = playlist.description || '';
        
        // Formatear fecha para el input datetime-local
        if (playlist.expiration_date) {
            try {
                const date = new Date(playlist.expiration_date);
                // Asegurarse de que la zona horaria se maneje correctamente
                const localDatetime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
                    .toISOString()
                    .slice(0, 16);
                editExpirationInput.value = localDatetime;
            } catch (e) {
                console.error("Error al procesar fecha:", e);
                editExpirationInput.value = '';
            }
        } else {
            editExpirationInput.value = '';
        }
        
        editActiveCheckbox.checked = playlist.is_active || false;
        
        // Buscar los modales en el DOM
        const detailModal = document.getElementById('playlistDetailModal');
        const editModal = document.getElementById('editPlaylistModal');
        
        if (!detailModal || !editModal) {
            throw new Error("No se encontraron los modales necesarios");
        }
        
        // Cerrar modal de detalles de manera segura
        if (window.bootstrap) {
            try {
                const detailModalInstance = bootstrap.Modal.getInstance(detailModal);
                if (detailModalInstance) {
                    detailModalInstance.hide();
                }
            } catch (e) {
                console.error("Error al cerrar modal de detalles:", e);
            }
        }
        
        // Mostrar modal de edición después de un breve retardo
        setTimeout(() => {
            if (window.bootstrap) {
                try {
                    const editModalInstance = new bootstrap.Modal(editModal);
                    editModalInstance.show();
                } catch (e) {
                    console.error("Error al mostrar modal de edición:", e);
                    showToast("Error al abrir el formulario de edición. Por favor, inténtelo de nuevo.", 'error');
                }
            }
        }, 500);
    } catch (error) {
        console.error("Error al preparar playlist para edición:", error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Guardar cambios de una playlist
async function savePlaylistChanges() {
    try {
        console.log("Guardando cambios de playlist...");
        
        const editIdInput = document.getElementById('editPlaylistId');
        if (!editIdInput || !editIdInput.value) {
            throw new Error("No se ha definido ID de playlist para editar");
        }
        
        const playlistId = editIdInput.value;
        
        // Obtener los valores incluyendo fecha de inicio
        const editTitleInput = document.getElementById('editPlaylistTitle');
        const editDescriptionInput = document.getElementById('editPlaylistDescription');
        const editStartDateInput = document.getElementById('editPlaylistStartDate');
        const editExpirationInput = document.getElementById('editPlaylistExpiration');
        const editActiveCheckbox = document.getElementById('editPlaylistActive');
        
        if (!editTitleInput || !editDescriptionInput || !editExpirationInput || !editActiveCheckbox) {
            throw new Error("No se encontraron todos los campos del formulario");
        }
        
        const playlistData = {
            title: editTitleInput.value,
            description: editDescriptionInput.value || null,
            start_date: editStartDateInput ? editStartDateInput.value || null : null,
            expiration_date: editExpirationInput.value || null,
            is_active: editActiveCheckbox.checked
        };
        
        console.log("Enviando datos:", playlistData);
        
        const response = await fetch(`${API_URL}/playlists/${playlistId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(playlistData),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
        }
        
        const updatedPlaylist = await response.json();
        console.log("Playlist actualizada:", updatedPlaylist);
        
        showToast('Lista de reproducción actualizada correctamente', 'success');
        
        // Cerrar el modal de edición
        if (window.bootstrap) {
            try {
                const editModal = document.getElementById('editPlaylistModal');
                if (editModal) {
                    const editModalInstance = bootstrap.Modal.getInstance(editModal);
                    if (editModalInstance) {
                        editModalInstance.hide();
                    }
                }
            } catch (e) {
                console.error("Error al cerrar modal de edición:", e);
            }
        }
        
        // Recargar playlists y abrir detalles
        setTimeout(() => {
            try {
                loadPlaylists();
                openPlaylistDetail(parseInt(playlistId));
            } catch (error) {
                console.error("Error al recargar datos:", error);
            }
        }, 500);
        
    } catch (error) {
        console.error('Error al guardar cambios de la playlist:', error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Eliminar una playlist
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

// ----- GESTIÓN DE RASPBERRY PI -----

// Cargar playlists activas para Raspberry Pi
async function loadRaspberryActivePlaylists() {
    console.log("Cargando playlists activas para Raspberry Pi");
    
    // Obtener el contenedor de manera segura
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
        
        // Generar HTML para las playlists
        let raspberryHTML = '';
        
        if (!Array.isArray(activePlaylists) || activePlaylists.length === 0) {
            raspberryHTML = `
                <div class="alert alert-warning">
                    No hay listas de reproducción activas para dispositivos Raspberry Pi
                </div>
            `;
        } else {
            // Crear tabla
            raspberryHTML = `
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Título</th>
                            <th>Expiración</th>
                            <th>Videos</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${activePlaylists.map(playlist => `
                            <tr>
                                <td>${playlist.title || ''}</td>
                                <td>${playlist.expiration_date ? formatDate(playlist.expiration_date) : 'Sin expiración'}</td>
                                <td>${playlist.videos ? playlist.videos.length : 0} videos</td>
                                <td>
                                    <button class="btn btn-sm btn-primary" onclick="openPlaylistDetail(${playlist.id})">
                                        <i class="fas fa-eye"></i> Ver
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
        
        // Actualizar el contenedor
        raspberryActiveList.innerHTML = raspberryHTML;
        
    } catch (error) {
        console.error('Error al cargar playlists activas para Raspberry Pi:', error);
        
        // Mostrar mensaje de error
        if (raspberryActiveList) {
            raspberryActiveList.innerHTML = `
                <div class="alert alert-danger">
                    Error al cargar listas de reproducción activas: ${error.message}
                </div>
            `;
        }
        
        showToast(`Error al cargar listas activas para Raspberry Pi: ${error.message}`, 'error');
    }
}

// ----- INICIALIZACIÓN -----

document.addEventListener('DOMContentLoaded', function() {
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
            const target = activeTab.getAttribute('href');
            if (target === '#videos') {
                loadVideos();
            } else if (target === '#playlists') {
                loadPlaylists();
            } else if (target === '#raspberry') {
                loadRaspberryActivePlaylists();
            }
        }
    } catch (e) {
        console.error("Error al cargar datos iniciales:", e);
    }
    
    // Configurar event listeners para navegación por pestañas
    try {
        document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(e) {
                const target = e.target.getAttribute('href');
                if (target === '#videos') {
                    loadVideos();
                } else if (target === '#playlists') {
                    loadPlaylists();
                } else if (target === '#raspberry') {
                    loadRaspberryActivePlaylists();
                }
            });
        });
    } catch (e) {
        console.error("Error al configurar navigación por pestañas:", e);
    }
    
    // Configurar filtros y búsquedas de manera segura
    try {
        // Filtros de videos
        safeElementOperation('videoFilterExpiration', element => {
            element.addEventListener('change', function() {
                loadVideos(this.value);
            });
        });
        
        // Filtros de playlists
        safeElementOperation('playlistFilterStatus', element => {
            element.addEventListener('change', function() {
                loadPlaylists(this.value);
            });
        });
        
        // Búsqueda de videos
        safeElementOperation('videoSearchInput', element => {
            element.addEventListener('input', function() {
                if (this.value.length > 2 || this.value.length === 0) {
                    filterVideosByTitle(this.value);
                }
            });
        });
        
        safeElementOperation('clearVideoSearch', element => {
            element.addEventListener('click', function() {
                const searchInput = document.getElementById('videoSearchInput');
                if (searchInput) {
                    searchInput.value = '';
                }
                const filterSelect = document.getElementById('videoFilterExpiration');
                loadVideos(filterSelect ? filterSelect.value : 'all');
            });
        });
        
        // Búsqueda de playlists
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
    
    // Formularios de creación
    try {
        // Formulario de subida de video
        safeElementOperation('videoUploadForm', element => {
            element.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                
                // Agregar fecha de expiración si se ha especificado
                const expirationInput = document.getElementById('videoExpiration');
                if (expirationInput && expirationInput.value) {
                    formData.append('expiration_date', expirationInput.value);
                }
                
                uploadVideo(formData);
            });
        });
        
        // Formulario de creación de playlist
        safeElementOperation('playlistCreateForm', element => {
            element.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const playlistData = {
                    title: document.getElementById('playlistTitle')?.value || '',
                    description: document.getElementById('playlistDescription')?.value || null,
                    expiration_date: document.getElementById('playlistExpiration')?.value || null,
                    is_active: document.getElementById('playlistActive')?.checked || false
                };
                
                createPlaylist(playlistData);
            });
        });
    } catch (e) {
        console.error("Error al configurar formularios:", e);
    }
    
    // Botones de guardado
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
    window.originalLoadPlaylists = window.loadPlaylists;
    window.loadPlaylists = async function(filter = 'all') {
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
                    <tr>
                        <td colspan="7" class="text-center py-5">
                            <p>No hay listas de reproducción disponibles. ¡Crea tu primera lista!</p>
                        </td>
                    </tr>
                `;
                return;
            }
            
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
                        <span class="badge bg-secondary">${playlist.videos.length} videos</span>
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
        } catch (error) {
            console.error('Error al cargar playlists:', error);
            document.getElementById('playlistsList').innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-5">
                        <div class="alert alert-danger">Error al cargar listas de reproducción: ${error.message}</div>
                    </td>
                </tr>
            `;
        } finally {
            document.getElementById('playlistsLoading').style.display = 'none';
        }
    };

    // Modificar la función openPlaylistDetail para mostrar videos en tabla
    window.originalOpenPlaylistDetail = window.openPlaylistDetail;
    window.openPlaylistDetail = async function(playlistId) {
        currentPlaylistId = playlistId;
        try {
            const response = await fetch(`${API_URL}/playlists/${playlistId}`);
            if (!response.ok) throw new Error('Error al cargar detalles de la playlist');
            
            const playlist = await response.json();
            
            // Código existente para mostrar información de la playlist...
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
            
            // Configurar botones
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
            
            // Mostrar videos en la playlist (formato tabla)
            const playlistVideos = document.getElementById('playlistVideos');
            playlistVideos.innerHTML = '';
            
            if (playlist.videos.length === 0) {
                playlistVideos.innerHTML = '<tr><td colspan="4" class="text-center">No hay videos en esta lista</td></tr>';
            } else {
                playlist.videos.forEach(video => {
                    const videoExpired = video.expiration_date && isExpired(video.expiration_date);
                    const videoRow = document.createElement('tr');
                    videoRow.className = videoExpired ? 'table-danger' : '';
                    
                    videoRow.innerHTML = `
                        <td>${video.title}</td>
                        <td>${video.description || '<span class="text-muted">Sin descripción</span>'}</td>
                        <td>
                            ${video.expiration_date ? 
                                `<span class="badge ${videoExpired ? 'bg-danger' : 'bg-info'}">
                                    ${videoExpired ? 'Expirado' : 'Expira'}: ${formatDate(video.expiration_date)}
                                </span>` : 
                                '<span class="text-muted">Sin expiración</span>'}
                        </td>
                        <td>
                            <button class="btn btn-outline-danger" onclick="removeVideoFromPlaylist(${playlistId}, ${video.id})">
                                <i class="fas fa-times"></i> Eliminar
                            </button>
                        </td>
                    `;
                    playlistVideos.appendChild(videoRow);
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
            
            // Mostrar y configurar sección de dispositivos
            await loadPlaylistDevices(playlistId);
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
    };

    // Modificar la función loadPlaylistDevices para mostrar dispositivos en tabla
    window.originalLoadPlaylistDevices = window.loadPlaylistDevices;
    window.loadPlaylistDevices = async function(playlistId) {
        try {
            const response = await fetch(`${API_URL}/device-playlists/playlist/${playlistId}/devices`);
            if (!response.ok) throw new Error('Error al cargar dispositivos asignados');
            
            const assignedDevices = await response.json();
            
            // Obtener el contenedor de dispositivos
            const devicesContainer = document.getElementById('assignedDevicesContainer');
            if (!devicesContainer) return;
            
            // Limpiar contenido actual
            if (assignedDevices.length === 0) {
                devicesContainer.innerHTML = '<p class="text-center">No hay dispositivos asignados a esta lista</p>';
                return;
            }
            
            // Crear la tabla de dispositivos asignados
            const table = document.createElement('table');
            table.className = 'table table-sm table-hover';
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Nombre</th>
                        <th>Ubicación</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;
            
            const tbody = table.querySelector('tbody');
            
            assignedDevices.forEach(device => {
                const deviceRow = document.createElement('tr');
                deviceRow.className = device.is_active ? '' : 'table-warning';
                
                deviceRow.innerHTML = `
                    <td>${device.device_id}</td>
                    <td>${device.name}</td>
                    <td>${device.location || ''} ${device.tienda ? ' - ' + device.tienda : ''}</td>
                    <td>
                        <span class="badge ${device.is_active ? 'bg-success' : 'bg-danger'}">
                            ${device.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-outline-danger" onclick="removeDeviceFromPlaylist('${device.device_id}', ${playlistId})">
                            <i class="fas fa-times"></i> Eliminar
                        </button>
                    </td>
                `;
                tbody.appendChild(deviceRow);
            });
            
            devicesContainer.innerHTML = '';
            devicesContainer.appendChild(table);
            
        } catch (error) {
            console.error('Error al cargar dispositivos asignados:', error);
            const devicesContainer = document.getElementById('assignedDevicesContainer');
            if (devicesContainer) {
                devicesContainer.innerHTML = `<div class="alert alert-danger">Error al cargar dispositivos: ${error.message}</div>`;
            }
        }
    };

// Modificar la función loadRaspberryActivePlaylists para usar tablas
window.originalLoadRaspberryActivePlaylists = window.loadRaspberryActivePlaylists;
window.loadRaspberryActivePlaylists = async function() {
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
                    <th>ID</th>
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
                <td>${playlist.id}</td>
                <td>${playlist.title}</td>
                <td>${playlist.expiration_date ? formatDate(playlist.expiration_date) : 'Sin expiración'}</td>
                <td>${playlist.videos.length} videos</td>
                <td>
                    <button class="btn btn-primary" onclick="openPlaylistDetail(${playlist.id})">
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
};

// Ajustar la función addDeviceToPlaylist que parece estar incompleta en el código original
window.addDeviceToPlaylist = async function(playlistId, deviceId) {
    try {
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
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al añadir el dispositivo');
        }
        
        alert('Dispositivo añadido a la lista correctamente');
        
        // Recargar dispositivos
        await loadPlaylistDevices(playlistId);
        await loadAvailableDevices(playlistId);
        
    } catch (error) {
        console.error('Error al añadir dispositivo a playlist:', error);
        alert(`Error al añadir el dispositivo a la lista: ${error.message}`);
    }
};
});

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
    
    // Actualizar información de paginación si existe
    const paginationInfo = document.getElementById('playlistPaginationInfo');
    if (paginationInfo) {
        paginationInfo.textContent = `Mostrando ${startItem} - ${endItem} de ${totalPlaylistItems} resultados`;
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

// Actualizar botones de paginación
function updatePlaylistPaginationButtons() {
    // Esta función se puede expandir cuando agregues los controles de paginación al HTML
    console.log(`Página ${currentPlaylistPage} de ${totalPlaylistPages}`);
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

// Event listeners para paginación de playlists
document.addEventListener('DOMContentLoaded', function() {
    
    // Filtro de estado de playlists
    const playlistFilterStatus = document.getElementById('playlistFilterStatus');
    if (playlistFilterStatus) {
        playlistFilterStatus.addEventListener('change', function() {
            currentPlaylistFilter = this.value;
            currentPlaylistPage = 1;
            applyPlaylistFiltersAndSearch();
        });
    }

    // Búsqueda de playlists con debounce
    const playlistSearchInput = document.getElementById('playlistSearchInput');
    if (playlistSearchInput) {
        playlistSearchInput.addEventListener('input', debounce(function() {
            searchPlaylists();
        }, 300));
    }

    // Limpiar búsqueda de playlists
    const clearPlaylistSearch = document.getElementById('clearPlaylistSearch');
    if (clearPlaylistSearch) {
        clearPlaylistSearch.addEventListener('click', function() {
            clearPlaylistSearch();
        });
    }

    // Si tienes un selector de tamaño de página, agregar event listener
    const playlistPageSizeSelect = document.getElementById('playlistPageSizeSelect');
    if (playlistPageSizeSelect) {
        playlistPageSizeSelect.addEventListener('change', function() {
            changePlaylistPageSize(this.value);
        });
    }
});

// Sobrescribir la función original para mantener compatibilidad
if (typeof window.loadPlaylists !== 'undefined') {
    const originalLoadPlaylists = window.loadPlaylists;
}
window.loadPlaylists = loadPlaylists;

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

console.log('Módulo de paginación de playlists cargado correctamente');