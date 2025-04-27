/**
 * service_manager.js
 * Script para gestionar servicios de dispositivos a través de la API.
 */

// Configuración
const API_BASE_URL = '/api/device-services';

/**
 * Gestiona un servicio en un dispositivo a través de la API
 * 
 * @param {string} deviceId - ID del dispositivo
 * @param {string} serviceName - Nombre del servicio (videoloop, kiosk)
 * @param {string} action - Acción a realizar (start, stop, restart, enable, disable, status)
 * @param {function} successCallback - Función a ejecutar en caso de éxito
 * @param {function} errorCallback - Función a ejecutar en caso de error
 */
function manageServiceViaApi(deviceId, serviceName, action, successCallback, errorCallback) {
    // Verificar parámetros
    if (!deviceId || !serviceName || !action) {
        console.error('Error: Faltan parámetros para la gestión de servicios');
        if (errorCallback) {
            errorCallback('Faltan parámetros para la gestión de servicios');
        }
        return;
    }
    
    // URL del endpoint
    const apiUrl = `${API_BASE_URL}/${deviceId}/${serviceName}/${action}`;
    console.log(`Enviando petición a: ${apiUrl}`);
    
    // Mostrar indicador de carga antes de enviar la petición
    showLoadingState(serviceName, action, true);
    
    // Realizar petición a la API
    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.detail || `Error ${response.status}: ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Respuesta del servidor:', data);
        
        // Ocultar indicador de carga
        showLoadingState(serviceName, action, false);
        
        // Si hay callback de éxito, llamar con los datos de respuesta
        if (successCallback) {
            successCallback(data);
        }
        
        // Actualizar la UI según el resultado
        updateServiceUI(deviceId, serviceName, data);
        
        // Mostrar notificación de éxito si la operación fue exitosa
        if (data.success) {
            showServiceNotification(
                'success',
                `Operación exitosa: ${action} ${serviceName}`,
                data.message
            );
        } else {
            showServiceNotification(
                'warning',
                `Advertencia: ${action} ${serviceName}`,
                data.message
            );
        }
    })
    .catch(error => {
        console.error('Error al gestionar servicio:', error);
        
        // Ocultar indicador de carga
        showLoadingState(serviceName, action, false);
        
        // Si hay callback de error, llamar con el error
        if (errorCallback) {
            errorCallback(error.message);
        }
        
        // Mostrar notificación de error
        showServiceNotification(
            'error',
            `Error al ${action} el servicio ${serviceName}`,
            error.message
        );
    });
}

/**
 * Actualiza la interfaz de usuario con el resultado de la operación
 * 
 * @param {string} deviceId - ID del dispositivo
 * @param {string} serviceName - Nombre del servicio
 * @param {object} data - Datos de respuesta de la API
 */
function updateServiceUI(deviceId, serviceName, data) {
    // Actualizar el badge de estado
    const statusBadge = document.getElementById(`${serviceName}-status-badge`);
    if (statusBadge) {
        statusBadge.className = `badge ${data.status === 'running' ? 'bg-success' : 'bg-danger'}`;
        statusBadge.textContent = data.status === 'running' ? 'En ejecución' : 'Detenido';
    }
    
    // Actualizar botones de acción
    const actionsContainer = document.getElementById(`${serviceName}-actions`);
    if (actionsContainer) {
        let buttonsHtml = '';
        
        if (data.status === 'running') {
            buttonsHtml = `
                <button type="button" class="btn btn-sm btn-danger service-action" 
                        data-service="${serviceName}" data-action="stop">
                    <i class="bi bi-stop-fill me-1"></i>Detener
                </button>
                <button type="button" class="btn btn-sm btn-warning service-action" 
                        data-service="${serviceName}" data-action="restart">
                    <i class="bi bi-arrow-repeat me-1"></i>Reiniciar
                </button>
            `;
        } else {
            buttonsHtml = `
                <button type="button" class="btn btn-sm btn-success service-action" 
                        data-service="${serviceName}" data-action="start">
                    <i class="bi bi-play-fill me-1"></i>Iniciar
                </button>
            `;
        }
        
        actionsContainer.innerHTML = buttonsHtml;
        
        // Volver a agregar event listeners a los nuevos botones
        initServiceActionButtons(actionsContainer);
    }
    
    // Actualizar toggle de habilitación
    const enableToggle = document.getElementById(`${serviceName}-enabled`);
    if (enableToggle && data.enabled) {
        enableToggle.checked = data.enabled === 'enabled';
        const label = enableToggle.nextElementSibling;
        if (label) {
            label.textContent = data.enabled === 'enabled' ? 'Habilitado' : 'Deshabilitado';
        }
    }
    
    // Actualizar sección de resultado si existe
    const resultSection = document.getElementById('service-action-result');
    const messageSection = document.getElementById('service-action-message');
    if (resultSection && messageSection) {
        resultSection.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-info');
        resultSection.classList.add(data.success ? 'alert-success' : 'alert-danger');
        
        messageSection.innerHTML = `
            <strong>${data.success ? 'Éxito' : 'Error'}:</strong> ${data.message}
            ${data.details ? `<pre class="mt-2 p-2 bg-light">${data.details}</pre>` : ''}
        `;
        
        // Desplazar a la sección de resultado
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }
}

/**
 * Muestra u oculta el estado de carga en los botones de acción
 * 
 * @param {string} serviceName - Nombre del servicio
 * @param {string} action - Acción que se está realizando
 * @param {boolean} isLoading - Si se debe mostrar el estado de carga
 */
function showLoadingState(serviceName, action, isLoading) {
    // Buscar el botón específico
    const actionButton = document.querySelector(`.service-action[data-service="${serviceName}"][data-action="${action}"]`);
    
    // Si encontramos el botón específico, actualizarlo
    if (actionButton) {
        if (isLoading) {
            // Guardar el texto original
            const originalText = actionButton.innerHTML;
            actionButton.dataset.originalText = originalText;
            
            // Mostrar spinner
            actionButton.innerHTML = `
                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                <span class="visually-hidden">Cargando...</span>
            `;
            actionButton.disabled = true;
        } else {
            // Restaurar texto original
            if (actionButton.dataset.originalText) {
                actionButton.innerHTML = actionButton.dataset.originalText;
                delete actionButton.dataset.originalText;
            }
            actionButton.disabled = false;
        }
    } else {
        // Si no encontramos el botón específico, actualizar todos los botones de ese servicio
        const buttons = document.querySelectorAll(`.service-action[data-service="${serviceName}"]`);
        buttons.forEach(button => {
            button.disabled = isLoading;
        });
        
        // También actualizar el toggle si existe
        const toggle = document.getElementById(`${serviceName}-enabled`);
        if (toggle) {
            toggle.disabled = isLoading;
        }
    }
}

/**
 * Muestra una notificación en la interfaz de usuario
 * 
 * @param {string} type - Tipo de notificación ('success', 'error', 'warning', 'info')
 * @param {string} title - Título de la notificación
 * @param {string} message - Mensaje de la notificación
 */
function showServiceNotification(type, title, message) {
    // Mapear tipo a clase de Bootstrap
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    // Crear el elemento de alerta
    const alertElement = document.createElement('div');
    alertElement.className = `alert ${alertClass} alert-dismissible fade show mt-3`;
    alertElement.innerHTML = `
        <strong>${title}</strong>
        <p>${message}</p>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Buscar contenedor para la notificación
    const container = document.querySelector('.card-body') || document.body;
    
    // Insertar al principio del contenedor
    container.insertBefore(alertElement, container.firstChild);
    
    // Configurar eliminación automática después de 5 segundos
    setTimeout(() => {
        if (alertElement.parentNode) {
            alertElement.classList.remove('show');
            setTimeout(() => {
                if (alertElement.parentNode) {
                    alertElement.parentNode.removeChild(alertElement);
                }
            }, 300);
        }
    }, 5000);
}

/**
 * Inicializa los botones de acción de servicio agregando event listeners
 * 
 * @param {HTMLElement} container - Contenedor de los botones (opcional)
 */
function initServiceActionButtons(container) {
    // Si no se proporciona un contenedor, usar todo el documento
    const root = container || document;
    
    // Buscar todos los botones de acción de servicio
    const actionButtons = root.querySelectorAll('.service-action');
    
    // Agregar event listener a cada botón
    actionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const serviceName = this.dataset.service;
            const action = this.dataset.action;
            const deviceId = getDeviceIdFromUrl();
            
            // Confirmar acción
            if (confirm(`¿Está seguro que desea ${actionVerb(action)} el servicio ${serviceName}?`)) {
                manageServiceViaApi(deviceId, serviceName, action);
            }
        });
    });
    
    // Inicializar toggles de habilitación
    const enableToggles = root.querySelectorAll('.service-enable-toggle');
    enableToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const serviceName = this.dataset.service;
            const action = this.checked ? 'enable' : 'disable';
            const deviceId = getDeviceIdFromUrl();
            
            manageServiceViaApi(deviceId, serviceName, action);
        });
    });
}

/**
 * Obtiene el ID del dispositivo desde la URL actual
 * 
 * @returns {string} ID del dispositivo
 */
function getDeviceIdFromUrl() {
    const pathParts = window.location.pathname.split('/');
    const deviceIdIndex = pathParts.indexOf('devices') + 1;
    
    if (deviceIdIndex > 0 && deviceIdIndex < pathParts.length) {
        return pathParts[deviceIdIndex];
    }
    
    // Intentar obtener desde un campo oculto si existe
    const deviceIdField = document.getElementById('device_id');
    if (deviceIdField) {
        return deviceIdField.value;
    }
    
    console.error('No se pudo determinar el ID del dispositivo');
    return '';
}

/**
 * Convierte una acción en un verbo legible
 * 
 * @param {string} action - Acción a convertir
 * @returns {string} Verbo correspondiente
 */
function actionVerb(action) {
    const verbs = {
        'start': 'iniciar',
        'stop': 'detener',
        'restart': 'reiniciar',
        'enable': 'habilitar',
        'disable': 'deshabilitar',
        'status': 'verificar'
    };
    
    return verbs[action] || action;
}

/**
 * Verifica el estado actual de los servicios en el dispositivo
 * 
 * @param {string} deviceId - ID del dispositivo
 */
function checkServicesStatus(deviceId) {
    if (!deviceId) {
        deviceId = getDeviceIdFromUrl();
    }
    
    // Verificar los servicios conocidos
    const services = ['videoloop', 'kiosk'];
    
    services.forEach(serviceName => {
        manageServiceViaApi(deviceId, serviceName, 'status');
    });
}

// Inicializar cuando el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar botones de acción
    initServiceActionButtons();
    
    // Verificar estado actual de los servicios
    checkServicesStatus();
    
    console.log('Gestor de servicios inicializado');
});

// Exportar funciones para uso externo
window.ServiceManager = {
    manage: manageServiceViaApi,
    checkStatus: checkServicesStatus,
    showNotification: showServiceNotification
};

/**
 * Verifica el estado actual de los servicios en el dispositivo
 * 
 * @param {string} deviceId - ID del dispositivo
 */
function checkServicesStatus(deviceId) {
    if (!deviceId) {
        deviceId = getDeviceIdFromUrl();
    }
    
    console.log(`Verificando estado de servicios para dispositivo ${deviceId}`);
    
    // Usar el nuevo endpoint que obtiene todos los servicios de una vez
    fetch(`${API_BASE_URL}/${deviceId}/all-services`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || `Error ${response.status}: ${response.statusText}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Estado de servicios:', data);
            
            if (!data.success) {
                console.error('Error al obtener estado de servicios:', data.message);
                showServiceNotification('warning', 'Estado de servicios', data.message);
                return;
            }
            
            // Actualizar la UI para cada servicio
            const services = data.services;
            for (const [serviceName, serviceData] of Object.entries(services)) {
                console.log(`Actualizando UI para servicio ${serviceName}:`, serviceData);
                
                // Crear un objeto de datos con el formato esperado por updateServiceUI
                const serviceUIData = {
                    success: true,
                    status: serviceData.status,
                    enabled: serviceData.enabled,
                    service: serviceName
                };
                
                // Actualizar la UI para este servicio
                updateServiceUI(deviceId, serviceName, serviceUIData);
            }
        })


}