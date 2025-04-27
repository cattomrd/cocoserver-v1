document.addEventListener('DOMContentLoaded', function() {
    // Inicializar los tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const deviceId = '{{ device.device_id }}';

    // ===== SECCIÓN DE PING =====
    initPingFunctionality();
    
    // ===== SECCIÓN DE CAMBIO DE HOSTNAME =====
    initHostnameChangeFunctionality();
    
    // ===== SECCIÓN DE LOGS =====
    initLogsFunctionality();
    
    // ===== SECCIÓN DE GESTIÓN DE SERVICIOS =====
    initServiceManagement();

    // ===== SECCIÓN DE CAPTURA DE PANTALLA =====
    initScreenshotFunctionality();
    // ===== FUNCIONES DE INICIALIZACIÓN =====
    
    function initPingFunctionality() {
        const pingButton = document.getElementById('pingButton');
        if (!pingButton) return;
        
        pingButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Cambiar el texto del botón mientras hace la verificación
            pingButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Verificando...';
            pingButton.disabled = true;
            
            // Realizar la solicitud AJAX
            fetch(`/api/devices/${deviceId}/ping`)
                .then(response => response.json())
                .then(data => {
                    // Actualizar la interfaz con el resultado
                    const statusBadge = document.getElementById('deviceStatusBadge');
                    if (statusBadge) {
                        if (data.is_active) {
                            statusBadge.className = 'badge bg-success';
                            statusBadge.textContent = 'Activo';
                        } else {
                            statusBadge.className = 'badge bg-danger';
                            statusBadge.textContent = 'Inactivo';
                        }
                    }
                    
                    // Mostrar notificación
                    const alertBox = document.createElement('div');
                    alertBox.className = `alert ${data.is_active ? 'alert-success' : 'alert-warning'} alert-dismissible fade show mt-3`;
                    alertBox.innerHTML = `
                        <strong>${data.is_active ? '¡Dispositivo Activo!' : 'Dispositivo Inactivo'}</strong>
                        <p>Ping a ${data.name} (${data.ip_address_lan || data.ip_address_wifi}): ${data.is_active ? 'Exitoso' : 'Fallido'}</p>
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    
                    // Insertar la notificación antes de la tabla de información
                    const cardBody = document.querySelector('.card-body');
                    cardBody.insertBefore(alertBox, cardBody.firstChild);
                    
                    // Restaurar el botón
                    pingButton.innerHTML = 'Verificar Estado (Ping)';
                    pingButton.disabled = false;
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Mostrar error
                    const cardBody = document.querySelector('.card-body');
                    const alertBox = document.createElement('div');
                    alertBox.className = 'alert alert-danger alert-dismissible fade show mt-3';
                    alertBox.innerHTML = `
                        <strong>Error</strong>
                        <p>No se pudo completar la verificación. Inténtalo de nuevo más tarde.</p>
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    cardBody.insertBefore(alertBox, cardBody.firstChild);
                    
                    // Restaurar el botón
                    pingButton.innerHTML = 'Verificar Estado (Ping)';
                    pingButton.disabled = false;
                });
        });
    }
    
    function initHostnameChangeFunctionality() {
        const newHostnameInput = document.getElementById('new_hostname');
        const confirmHostnameInput = document.getElementById('confirm_hostname');
        const hostnameMatchError = document.getElementById('hostnameMatchError');
        const validateSshBtn = document.getElementById('validateSshBtn');
        const submitHostnameBtn = document.getElementById('submitHostnameBtn');
        const sshStatusContainer = document.getElementById('sshStatusContainer');
        const sshStatus = document.getElementById('sshStatus');
        
        if (!newHostnameInput || !confirmHostnameInput) return;
        
        // Validar que los hostnames coinciden
        function validateHostnameMatch() {
            // Solo validar si ambos campos tienen contenido
            if (newHostnameInput.value && confirmHostnameInput.value) {
                if (newHostnameInput.value === confirmHostnameInput.value) {
                    confirmHostnameInput.classList.remove('is-invalid');
                    hostnameMatchError.style.display = 'none';
                    
                    // Verificar si ya pasamos la validación SSH
                    const sshValidated = sshStatusContainer && 
                                        !sshStatusContainer.classList.contains('d-none') && 
                                        sshStatus && 
                                        sshStatus.classList.contains('alert-success');
                    
                    // Habilitar el botón si la SSH está validada
                    if (sshValidated) {
                        submitHostnameBtn.disabled = false;
                    }
                    
                    return true;
                } else {
                    confirmHostnameInput.classList.add('is-invalid');
                    hostnameMatchError.style.display = 'block';
                    submitHostnameBtn.disabled = true;
                    return false;
                }
            }
            
            // Si algún campo está vacío, no mostrar error pero retornar false
            return false;
        }
        
        // Validar conexión SSH
        if (validateSshBtn) {
            validateSshBtn.addEventListener('click', function() {
                // Mostrar contenedor de estado
                sshStatusContainer.classList.remove('d-none');
                sshStatus.className = 'alert alert-info';
                sshStatus.textContent = 'Verificando conexión SSH...';
                validateSshBtn.disabled = true;
                
                // Realizar la solicitud de validación
                fetch(`/api/devices/${deviceId}/ssh/validate`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            sshStatus.className = 'alert alert-success';
                            sshStatus.textContent = data.message;
                            
                            // Habilitar botón de envío si ambas validaciones pasan
                            if (validateHostnameMatch()) {
                                submitHostnameBtn.disabled = false;
                            }
                        } else {
                            sshStatus.className = 'alert alert-danger';
                            sshStatus.textContent = data.message;
                            submitHostnameBtn.disabled = true;
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        sshStatus.className = 'alert alert-danger';
                        sshStatus.textContent = 'Error al verificar la conexión SSH';
                        submitHostnameBtn.disabled = true;
                    })
                    .finally(() => {
                        validateSshBtn.disabled = false;
                    });
            });
        }
        
        // Validar coincidencia al cambiar los campos
        newHostnameInput.addEventListener('input', validateHostnameMatch);
        confirmHostnameInput.addEventListener('input', validateHostnameMatch);
        
        // Manejar el cambio de hostname
        if (submitHostnameBtn) {
            submitHostnameBtn.addEventListener('click', function() {
                if (!validateHostnameMatch()) {
                    return;
                }
                
                // Mostrar indicador de carga
                submitHostnameBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Cambiando...';
                submitHostnameBtn.disabled = true;
                
                // Enviar formulario mediante AJAX
                const formData = new FormData();
                formData.append('new_hostname', newHostnameInput.value);
                
                fetch(`/api/devices/${deviceId}/hostname`, {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.detail || 'Error al cambiar el hostname');
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    // Éxito - mostrar notificación y recargar después de un tiempo
                    if (data.reboot) {
                        // Notificar que el dispositivo se está reiniciando
                        let message = `Hostname cambiado exitosamente de ${data.old_hostname} a ${data.new_hostname}. El dispositivo se está reiniciando. `;
                        message += `La página se recargará en 90 segundos para darle tiempo al dispositivo a reiniciarse.`;
                        alert(message);
                        
                        // Esperar más tiempo para dar oportunidad al reinicio (90 segundos)
                        setTimeout(() => {
                            window.location.href = `/ui/devices/${data.new_hostname}`;
                        }, 90000); // 90 segundos
                    } else {
                        // Comportamiento anterior sin reinicio
                        alert(`Hostname cambiado exitosamente de ${data.old_hostname} a ${data.new_hostname}. La página se recargará en 3 segundos.`);
                        setTimeout(() => {
                            window.location.href = `/ui/devices/${data.new_hostname}`;
                        }, 3000); // 3 segundos
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Mostrar error
                    sshStatus.className = 'alert alert-danger';
                    sshStatus.textContent = error.message;
                    // Restaurar botón
                    submitHostnameBtn.innerHTML = 'Cambiar Hostname';
                    submitHostnameBtn.disabled = false;
                });
            });
        }
    }
    
    function initLogsFunctionality() {
        const deviceLogContent = document.getElementById('deviceLogContent');
        const refreshLogsBtn = document.getElementById('refreshLogsBtn');
        const lastLogUpdate = document.getElementById('lastLogUpdate');
        
        if (!deviceLogContent || !refreshLogsBtn) return;
        
        // Función para formatear la fecha actual
        function formatDateTime() {
            const now = new Date();
            return now.toLocaleString();
        }
        
        // Función para procesar el texto del log

        
        // Función para cargar los logs
async function loadDeviceLogs() {
    try {
        // Mostrar indicador de carga
        deviceLogContent.textContent = 'Cargando logs...';
        
        // Realizar la petición al endpoint
        const response = await fetch(`/api/devices/${deviceId}/logs`);
        
        if (response.ok) {
            // Obtener los datos de texto plano
            const rawLogData = await response.text();
            
            // Procesar el texto para asegurar saltos de línea correctos
            const processedLogData = processLogText(rawLogData);
            
            // Asignar el contenido procesado
            deviceLogContent.textContent = processedLogData;
            
            // Resaltar diferentes niveles de log con colores
            const formattedHtml = processedLogData
                .replace(/ERROR/g, '<span style="color: #ff6b6b;">ERROR</span>')
                .replace(/WARNING/g, '<span style="color: #feca57;">WARNING</span>')
                .replace(/INFO/g, '<span style="color: #48dbfb;">INFO</span>');
            
            // Usar innerHTML SOLO después de procesar el HTML de forma segura
            deviceLogContent.innerHTML = formattedHtml;
            
            // Actualizar la hora de la última actualización
            if (lastLogUpdate) {
                lastLogUpdate.textContent = formatDateTime();
            }
            
            // Desplazar automáticamente al final del contenedor de logs
            const logContainer = document.querySelector('.log-container');
            if (logContainer) {
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        } else {
            // Mostrar mensaje de error en caso de fallo en la petición
            deviceLogContent.textContent = `Error al cargar logs: ${response.status} ${response.statusText}`;
        }
    } catch (error) {
        // Mostrar mensaje de error en caso de excepción
        deviceLogContent.textContent = `Error al cargar logs: ${error.message}`;
        console.error('Error al cargar logs:', error);
    }
}

function processLogText(text) {
    // 1. Reemplazar literales \n con verdaderos saltos de línea
    let processedText = text.replace(/\\n/g, '\n');
    
    // 2. También eliminar comillas al principio y final si están presentes
    if (processedText.startsWith('"') && processedText.endsWith('"')) {
        processedText = processedText.substring(1, processedText.length - 1);
    }
    
    return processedText;
}
        
    // Configurar el botón de actualizar
    refreshLogsBtn.addEventListener('click', function(event) {
        event.preventDefault();
        loadDeviceLogs();
    });
    
    // Cargar logs al iniciar la página
    loadDeviceLogs();
}
    
function initServiceManagement() {
const serviceActionButtons = document.querySelectorAll('.service-action');
const serviceEnableToggles = document.querySelectorAll('.service-enable-toggle');
const serviceActionModal = document.getElementById('serviceActionModal');
const confirmServiceActionBtn = document.getElementById('confirmServiceAction');
const serviceActionSpinner = document.getElementById('serviceActionSpinner');
const serviceActionResult = document.getElementById('service-action-result');
const serviceActionMessage = document.getElementById('service-action-message');

if (!serviceActionButtons.length || !serviceActionModal) return;

// Inicializar el modal de Bootstrap
const modal = new bootstrap.Modal(serviceActionModal);

// Variables para almacenar la acción actual
let currentService = null;
let currentAction = null;

// Función para actualizar la UI después de una acción
function updateServiceUI(service, status, enabled) {
    const statusBadge = document.getElementById(`${service}-status-badge`);
    const actionsContainer = document.getElementById(`${service}-actions`);
    const enableToggle = document.getElementById(`${service}-enabled`);
    
    // Actualizar la badge de estado
    if (statusBadge) {
        statusBadge.className = `badge ${status === 'running' ? 'bg-success' : 'bg-danger'}`;
        statusBadge.textContent = status === 'running' ? 'En ejecución' : 'Detenido';
    }
    
    // Actualizar botones de acción
    if (actionsContainer) {
        let buttonsHtml = '';
        
        if (status === 'running') {
            buttonsHtml = `
                <button type="button" class="btn btn-sm btn-danger service-action" data-service="${service}" data-action="stop">
                    <i class="bi bi-stop-fill me-1"></i>Detener
                </button>
                <button type="button" class="btn btn-sm btn-warning service-action" data-service="${service}" data-action="restart">
                    <i class="bi bi-arrow-repeat me-1"></i>Reiniciar
                </button>
            `;
        } else {
            buttonsHtml = `
                <button type="button" class="btn btn-sm btn-success service-action" data-service="${service}" data-action="start">
                    <i class="bi bi-play-fill me-1"></i>Iniciar
                </button>
            `;
        }
        
        actionsContainer.innerHTML = buttonsHtml;
        
        // Volver a agregar event listeners a los nuevos botones
        actionsContainer.querySelectorAll('.service-action').forEach(button => {
            button.addEventListener('click', handleServiceAction);
        });
    }
    
    // Actualizar toggle de habilitación
    if (enableToggle && enabled !== undefined) {
        enableToggle.checked = enabled === 'enabled';
        const label = enableToggle.nextElementSibling;
        if (label) {
            label.textContent = enabled === 'enabled' ? 'Habilitado' : 'Deshabilitado';
        }
    }
}
        
// Función para manejar el clic en botones de acción
function handleServiceAction(event) {
    const button = event.currentTarget;
    currentService = button.dataset.service;
    currentAction = button.dataset.action;
    
    // Configurar el modal de confirmación
    const confirmMessage = document.getElementById('serviceActionConfirmMessage');
    let actionText = '';
    
    switch (currentAction) {
        case 'start':
            actionText = 'iniciar';
            break;
        case 'stop':
            actionText = 'detener';
            break;
        case 'restart':
            actionText = 'reiniciar';
            break;
        case 'status':
            actionText = 'verificar el estado de';
            break;
    }
    
    confirmMessage.textContent = `¿Está seguro que desea ${actionText} el servicio ${currentService}?`;
    serviceActionSpinner.classList.add('d-none');
    
    // Mostrar el modal de confirmación
    modal.show();
}
        
// Función para ejecutar la acción del servicio
async function executeServiceAction() {
    try {
        // Mostrar spinner
        serviceActionSpinner.classList.remove('d-none');
        confirmServiceActionBtn.disabled = true;
        
        // Realizar la petición a la API
        const response = await fetch(`/services/${deviceId}/service/${currentService}/${currentAction}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Error al ${currentAction} servicio: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Cerrar el modal
        modal.hide();
        
        // Mostrar resultado
        serviceActionResult.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info');
        serviceActionResult.classList.add(result.success ? 'alert-success' : 'alert-danger');
        serviceActionMessage.innerHTML = `
            <strong>${result.success ? 'Éxito' : 'Error'}:</strong> ${result.message}
            ${result.details ? `<pre class="mt-2 p-2 bg-light">${result.details}</pre>` : ''}
        `;
        
        // Actualizar UI si tuvo éxito
        if (result.success) {
            if (currentAction === 'start' || currentAction === 'stop' || currentAction === 'restart') {
                updateServiceUI(currentService, result.status, undefined);
            }
        }
        
        // Desplazar a la sección de resultado
        serviceActionResult.scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        console.error('Error:', error);
        serviceActionResult.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info');
        serviceActionResult.classList.add('alert-danger');
        serviceActionMessage.textContent = `Error: ${error.message}`;
    } finally {
        // Ocultar spinner y rehabilitar botón
        serviceActionSpinner.classList.add('d-none');
        confirmServiceActionBtn.disabled = false;
    }
}
        
    // Función para manejar el toggle de habilitar/deshabilitar
    async function handleServiceToggle(event) {
    const toggle = event.currentTarget;
    const service = toggle.dataset.service;
    const action = toggle.checked ? 'enable' : 'disable';
    
    console.log(`Enviando petición para ${action} servicio ${service}`);
    
    try {
        // Desactivar el toggle mientras se procesa
        toggle.disabled = true;
        
        // Mostrar la URL completa para depuración
        const url = `/services/${deviceId}/service/${service}/${action}`;
        console.log("URL:", url);
        
        // Realizar la petición a la API
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // Loguear respuesta completa
        console.log("Respuesta:", response);
        
        if (!response.ok) {
            throw new Error(`Error al ${action} servicio: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log("Resultado:", result);
        // Cerrar el modal    
            // Mostrar resultado
            serviceActionResult.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info');
            serviceActionResult.classList.add(result.success ? 'alert-success' : 'alert-danger');
            serviceActionMessage.textContent = result.message;
            
            // Actualizar la UI
            if (result.success) {
                const label = toggle.nextElementSibling;
                if (label) {
                    label.textContent = toggle.checked ? 'Habilitado' : 'Deshabilitado';
                }
            } else {
                // Revertir el toggle si hubo error
                toggle.checked = !toggle.checked;
            }
            
        } catch (error) {
            console.error('Error:', error);
            serviceActionResult.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info');
            serviceActionResult.classList.add('alert-danger');
            serviceActionMessage.textContent = `Error: ${error.message}`;
            
            // Revertir el toggle si hubo error
            toggle.checked = !toggle.checked;
        } finally {
            // Reactivar el toggle
            toggle.disabled = false;
        }
    }
    
    // Agregar event listeners a los botones de acción
    serviceActionButtons.forEach(button => {
        button.addEventListener('click', handleServiceAction);
    });
    
    // Agregar event listener al botón de confirmación
    if (confirmServiceActionBtn) {
        confirmServiceActionBtn.addEventListener('click', executeServiceAction);
    }
    
    // Agregar event listeners a los toggles de habilitar/deshabilitar
    serviceEnableToggles.forEach(toggle => {
        toggle.addEventListener('change', handleServiceToggle);
    });
}
    function initScreenshotFunctionality() {
        const screenshotButton = document.getElementById('screenshotButton');
        const screenshotModal = document.getElementById('screenshotModal');
        const screenshotImage = document.getElementById('screenshotImage');
        const screenshotSpinner = document.getElementById('screenshotSpinner');
        const screenshotError = document.getElementById('screenshotError');
        const downloadScreenshotBtn = document.getElementById('downloadScreenshotBtn');
        const refreshScreenshotBtn = document.getElementById('refreshScreenshotBtn');
        
        if (!screenshotButton || !screenshotModal) return;
        
        // Inicializar el modal de Bootstrap
        const modal = new bootstrap.Modal(screenshotModal);
        
        // Función para obtener y mostrar la captura de pantalla
        async function getScreenshot() {
            try {
                // Mostrar spinner y ocultar elementos previos
                screenshotSpinner.classList.remove('d-none');
                screenshotImage.classList.add('d-none');
                screenshotError.classList.add('d-none');
                downloadScreenshotBtn.classList.add('d-none');
                
                // Realizar la petición a la API
                const response = await fetch(`/services/devices/${deviceId}/screenshot`);
                
                if (!response.ok) {
                    throw new Error(`Error al obtener la captura: ${response.status} ${response.statusText}`);
                }
                
                // Obtener la imagen como blob
                const imageBlob = await response.blob();
                
                // Crear URL para la imagen
                const imageUrl = URL.createObjectURL(imageBlob);
                
                // Mostrar la imagen
                screenshotImage.src = imageUrl;
                screenshotImage.classList.remove('d-none');
                
                // Configurar botón de descarga
                downloadScreenshotBtn.href = imageUrl;
                downloadScreenshotBtn.download = `screenshot-${deviceId}-${new Date().toISOString().replace(/:/g, '-')}.png`;
                downloadScreenshotBtn.classList.remove('d-none');
                
            } catch (error) {
                console.error('Error:', error);
                screenshotError.textContent = `Error al obtener la captura: ${error.message}`;
                screenshotError.classList.remove('d-none');
            } finally {
                // Ocultar spinner
                screenshotSpinner.classList.add('d-none');
            }
        }
        
        // Event listener para el botón de captura
        screenshotButton.addEventListener('click', function() {
            modal.show();
            getScreenshot();
        });
        
        // Event listener para el botón de actualizar
        refreshScreenshotBtn.addEventListener('click', getScreenshot);
        
        // Limpiar recursos cuando se cierra el modal
        screenshotModal.addEventListener('hidden.bs.modal', function() {
            if (screenshotImage.src) {
                URL.revokeObjectURL(screenshotImage.src);
            }
        });
    }
});

// Variables globales
const deviceId = '{{ device.device_id }}';
const now = new Date();
let allPlaylists = [];

// Función para cargar playlists asignadas
async function loadAssignedPlaylists() {
    try {
        const playlistsContainer = document.getElementById('playlistsContainer');
        if (!playlistsContainer) return;
        
        playlistsContainer.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Cargando listas...</p></div>';
        
        const response = await fetch(`/api/device-playlists/device/${deviceId}/playlists`);
        if (!response.ok) {
            throw new Error(`${response.status} ${response.statusText}`);
        }
        
        const playlists = await response.json();
        
        if (playlists.length === 0) {
            playlistsContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> Este dispositivo no tiene listas de reproducción asignadas.
                </div>
            `;
            return;
        }
        
        // Crear la tabla de playlists
        let html = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Título</th>
                            <th>Estado</th>
                            <th>Expiración</th>
                            <th>Videos</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        playlists.forEach(playlist => {
            const isActive = playlist.is_active && (!playlist.expiration_date || new Date(playlist.expiration_date) > now);
            const hasExpired = playlist.expiration_date && new Date(playlist.expiration_date) < now;
            
            html += `
                <tr>
                    <td>${playlist.title}</td>
                    <td>
                        <span class="badge ${isActive ? 'bg-success' : 'bg-danger'}">
                            ${isActive ? 'Activa' : 'Inactiva'}
                        </span>
                    </td>
                    <td>
                        ${playlist.expiration_date 
                            ? (hasExpired 
                                ? `<span class="badge bg-danger">Expirada: ${new Date(playlist.expiration_date).toLocaleDateString()}</span>` 
                                : `<span class="badge bg-info">${new Date(playlist.expiration_date).toLocaleDateString()}</span>`)
                            : '<span class="badge bg-secondary">Sin expiración</span>'
                        }
                    </td>
                    <td>${playlist.videos ? playlist.videos.length : 0}</td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-info" onclick="viewPlaylistDetails(${playlist.id})">
                                <i class="bi bi-eye"></i> Ver
                            </button>
                            <button class="btn btn-outline-danger" onclick="confirmRemovePlaylist('${deviceId}', ${playlist.id}, '${playlist.title}')">
                                <i class="bi bi-x-circle"></i> Quitar
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        playlistsContainer.innerHTML = html;
        
    } catch (error) {
        console.error('Error al cargar playlists asignadas:', error);
        const playlistsContainer = document.getElementById('playlistsContainer');
        if (playlistsContainer) {
            playlistsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> Error al cargar listas: ${error.message}
                </div>
            `;
        }
    }
}

// Función para cargar playlists disponibles para asignar
// Función para cargar playlists disponibles para asignar
async function loadAvailablePlaylists() {
    try {
        const showOnlyActive = document.getElementById('showOnlyActivePlaylistsCheck').checked;
        const selectElement = document.getElementById('availablePlaylistsSelect');
        
        if (!selectElement) return;
        
        selectElement.innerHTML = '<option value="">Cargando listas...</option>';
        
        // Primero, obtener todas las playlists
        const allPlaylistsResponse = await fetch(`/api/playlists/${showOnlyActive ? '?active_only=true' : ''}`);
        if (!allPlaylistsResponse.ok) {
            throw new Error(`Error al cargar listas: ${allPlaylistsResponse.status}`);
        }
        
        allPlaylists = await allPlaylistsResponse.json();
        
        // Luego, obtener las playlists ya asignadas
        const assignedPlaylistsResponse = await fetch(`/api/device-playlists/device/${deviceId}/playlists`);
        if (!assignedPlaylistsResponse.ok) {
            throw new Error(`Error al cargar listas asignadas: ${assignedPlaylistsResponse.status}`);
        }
        
        const assignedPlaylists = await assignedPlaylistsResponse.json();
        
        // Filtrar para obtener solo las playlists no asignadas
        const assignedPlaylistIds = assignedPlaylists.map(p => p.id);
        const availablePlaylists = allPlaylists.filter(p => !assignedPlaylistIds.includes(p.id));
        
        if (availablePlaylists.length === 0) {
            selectElement.innerHTML = '<option value="">No hay listas disponibles</option>';
            return;
        }
        
        selectElement.innerHTML = '<option value="">Seleccione una lista...</option>';
        
        // Añadir cada playlist al select
        availablePlaylists.forEach(playlist => {
            const option = document.createElement('option');
            option.value = playlist.id;
            
            // Mostrar el título y estado
            const isExpired = playlist.expiration_date && new Date(playlist.expiration_date) < now;
            const statusText = !playlist.is_active ? '(Inactiva)' : 
                              isExpired ? '(Expirada)' : '';
            
            option.textContent = `${playlist.title} ${statusText}`;
            
            // Añadir atributos data para poder usarlos después
            option.dataset.title = playlist.title;
            option.dataset.description = playlist.description || 'Sin descripción';
            option.dataset.active = playlist.is_active;
            option.dataset.expiration = playlist.expiration_date || '';
            option.dataset.videoCount = playlist.videos ? playlist.videos.length : 0;
            
            selectElement.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error al cargar listas disponibles:', error);
        const selectElement = document.getElementById('availablePlaylistsSelect');
        if (selectElement) {
            selectElement.innerHTML = `<option value="">Error: ${error.message}</option>`;
        }
    }
}

// Función para mostrar detalles de la playlist seleccionada
function showPlaylistPreview() {
    const selectElement = document.getElementById('availablePlaylistsSelect');
    const playlistPreview = document.getElementById('playlistPreview');
    
    if (!selectElement || !playlistPreview) return;
    
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    
    if (!selectedOption || !selectedOption.value) {
        playlistPreview.classList.add('d-none');
        return;
    }
    
    // Obtener datos del option seleccionado
    const title = selectedOption.dataset.title;
    const description = selectedOption.dataset.description;
    const isActive = selectedOption.dataset.active === 'true';
    const expiration = selectedOption.dataset.expiration;
    const videoCount = selectedOption.dataset.videoCount;
    
    // Actualizar elementos del preview
    document.getElementById('previewPlaylistTitle').textContent = title;
    document.getElementById('previewPlaylistDescription').textContent = description;
    
    const statusBadge = document.getElementById('previewPlaylistStatus');
    statusBadge.className = `badge ${isActive ? 'bg-success' : 'bg-danger'}`;
    statusBadge.textContent = isActive ? 'Activa' : 'Inactiva';
    
    const expirationBadge = document.getElementById('previewPlaylistExpiration');
    if (expiration) {
        const expirationDate = new Date(expiration);
        const hasExpired = expirationDate < now;
        
        expirationBadge.className = `badge ${hasExpired ? 'bg-danger' : 'bg-info'}`;
        expirationBadge.textContent = hasExpired ? 
            `Expirada: ${expirationDate.toLocaleDateString()}` : 
            `Expira: ${expirationDate.toLocaleDateString()}`;
    } else {
        expirationBadge.className = 'badge bg-secondary';
        expirationBadge.textContent = 'Sin expiración';
    }
    
    const videoBadge = document.getElementById('previewPlaylistVideos');
    videoBadge.textContent = `${videoCount} video${videoCount !== 1 ? 's' : ''}`;
    
    // Mostrar el preview
    playlistPreview.classList.remove('d-none');
}

// Asignar playlist a dispositivo
async function assignPlaylistToDevice() {
    const selectElement = document.getElementById('availablePlaylistsSelect');
    const playlistId = selectElement.value;
    
    if (!playlistId) {
        alert('Por favor, seleccione una lista de reproducción para asignar');
        return;
    }
    
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

// Confirmar la eliminación de una playlist
function confirmRemovePlaylist(deviceId, playlistId, playlistTitle) {
    const removePlaylistMessage = document.getElementById('removePlaylistMessage');
    const removePlaylistId = document.getElementById('removePlaylistId');
    const removeDeviceId = document.getElementById('removeDeviceId');
    
    if (!removePlaylistMessage || !removePlaylistId || !removeDeviceId) return;
    
    // Actualizar mensaje de confirmación
    removePlaylistMessage.textContent = `¿Está seguro que desea quitar la lista "${playlistTitle}" de este dispositivo?`;
    
    // Guardar los IDs para la eliminación
    removePlaylistId.value = playlistId;
    removeDeviceId.value = deviceId;
    
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('removePlaylistModal'));
    modal.show();
}

// Eliminar asignación de playlist a dispositivo
async function removePlaylistFromDevice() {
    const playlistId = document.getElementById('removePlaylistId').value;
    const deviceId = document.getElementById('removeDeviceId').value;
    
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
function viewPlaylistDetails(playlistId) {
    // Redirigir a la pestaña de playlists y mostrar los detalles de la playlist seleccionada
    window.location.href = `/ui/videos#playlists-${playlistId}`;
}

// Inicializar componentes
document.addEventListener('DOMContentLoaded', function() {
    // Referencias a elementos del DOM
    const availablePlaylistsSelect = document.getElementById('availablePlaylistsSelect');
    const showOnlyActivePlaylistsCheck = document.getElementById('showOnlyActivePlaylistsCheck');
    const confirmAssignPlaylistBtn = document.getElementById('confirmAssignPlaylistBtn');
    const confirmRemovePlaylistBtn = document.getElementById('confirmRemovePlaylistBtn');
    const refreshPlaylistsBtn = document.getElementById('refreshPlaylistsBtn');
    
    // Manejar cambio en el select de playlists disponibles
    if (availablePlaylistsSelect) {
        availablePlaylistsSelect.addEventListener('change', showPlaylistPreview);
    }
    
    // Inicializar componentes
    if (refreshPlaylistsBtn) {
        refreshPlaylistsBtn.addEventListener('click', loadAssignedPlaylists);
    }
    
    if (showOnlyActivePlaylistsCheck) {
        showOnlyActivePlaylistsCheck.addEventListener('change', loadAvailablePlaylists);
    }
    
    if (confirmAssignPlaylistBtn) {
        confirmAssignPlaylistBtn.addEventListener('click', assignPlaylistToDevice);
    }
    
    if (confirmRemovePlaylistBtn) {
        confirmRemovePlaylistBtn.addEventListener('click', removePlaylistFromDevice);
    }
    
    // Cargar datos iniciales
    loadAssignedPlaylists();
    loadAvailablePlaylists();
});