/**
 * Inicializa la funcionalidad del reinicio de dispositivo
 */
function initRestartFunctionality() {
    // Seleccionar elementos del DOM
    const deviceId = document.getElementById('device-id').value;
    const restartButton = document.getElementById('restartButton');
    const restartModal = document.getElementById('restartDeviceModal');
    const confirmRestartBtn = document.getElementById('confirmRestartBtn');
    const restartSpinner = document.getElementById('restartSpinner');
    
    // Verificar si los elementos existen
    if (!restartButton || !restartModal || !confirmRestartBtn) {
        console.error('No se encontraron los elementos necesarios para la funcionalidad de reinicio');
        return;
    }
    
    // Inicializar el modal usando Bootstrap
    const modal = new bootstrap.Modal(restartModal);
    
    // Event listener para mostrar el modal al hacer clic en el botón de reinicio
    restartButton.addEventListener('click', function() {
        // El modal se abrirá por el atributo data-bs-target="#restartDeviceModal" en el HTML
        console.log('Botón de reinicio clickeado');
    });
    
    // Event listener para el botón de confirmación
    confirmRestartBtn.addEventListener('click', async function() {
        try {
            // Mostrar spinner y deshabilitar botón
            restartSpinner.classList.remove('d-none');
            confirmRestartBtn.disabled = true;
            
            console.log(`Enviando petición de reinicio para el dispositivo: ${deviceId}`);
            
            // Realizar la petición a la API con la ruta correcta
            const response = await fetch(`/api/devices/${deviceId}/system/reboot`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            // Verificar la respuesta
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Respuesta del servidor:', data);
            
            // Cerrar el modal
            modal.hide();
            
            // Mostrar notificación de éxito
            showNotification(
                'Reinicio iniciado', 
                'El dispositivo se está reiniciando. Puede tardar hasta 1 minuto en completarse.', 
                'warning'
            );
            
            // Deshabilitar el botón de reinicio principal y cambiar su texto
            restartButton.disabled = true;
            restartButton.innerHTML = '<i class="bi bi-power"></i> Reiniciando...';
            
            // Programar una verificación después de 60 segundos
            setTimeout(function() {
                checkDeviceStatus(deviceId, restartButton);
            }, 60000);
            
        } catch (error) {
            console.error('Error al reiniciar dispositivo:', error);
            
            // Ocultar spinner y rehabilitar botón
            restartSpinner.classList.add('d-none');
            confirmRestartBtn.disabled = false;
            
            // Cerrar el modal
            modal.hide();
            
            // Mostrar notificación de error
            showNotification(
                'Error', 
                `No se pudo reiniciar el dispositivo: ${error.message}`, 
                'danger'
            );
        }
    });
}

/**
 * Verifica el estado del dispositivo después de un reinicio
 * @param {string} deviceId - ID del dispositivo
 * @param {HTMLElement} restartButton - Botón de reinicio para actualizar su estado
 */
async function checkDeviceStatus(deviceId, restartButton) {
    try {
        const response = await fetch(`/api/devices/${deviceId}/ping`);
        const data = await response.json();
        
        if (data.is_active) {
            // El dispositivo está en línea nuevamente
            showNotification(
                'Dispositivo en línea', 
                'El reinicio se ha completado exitosamente.', 
                'success'
            );
        } else {
            // El dispositivo sigue sin responder
            showNotification(
                'Verificación pendiente', 
                'El dispositivo aún no responde. Puede tardar más tiempo en reiniciarse.', 
                'info'
            );
        }
    } catch (error) {
        console.error('Error al verificar estado:', error);
        showNotification(
            'Error de verificación', 
            'No se pudo verificar el estado del dispositivo después del reinicio.', 
            'warning'
        );
    } finally {
        // Restaurar el botón de reinicio independientemente del resultado
        restartButton.disabled = false;
        restartButton.innerHTML = '<i class="bi bi-power"></i> Reiniciar';
    }
}

// Asegurarse de que la función se llame cuando el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    initRestartFunctionality();
});