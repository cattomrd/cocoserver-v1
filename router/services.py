from fastapi import APIRouter, Request, Depends, HTTPException, Response, BackgroundTasks  # Añadido BackgroundTask
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional
import requests
import tempfile
import sys
import os
import paramiko
import logging  # Asegúrate de tener paramiko instalado
from utils import ssh_helper

from models import models
from models.database import SessionLocal, get_db

from models import models
from models.database import SessionLocal, get_db
router = APIRouter(
    prefix="/api/services",
    tags=["services"]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'my_static_files'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Configuración SSH
# Actualización parcial de router/services.py

# Configuración SSH con variables de entorno
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH')  # Ruta a la clave SSH privada
SSH_USER = os.environ.get('SSH_USER')  # Usuario SSH
SSH_PORT = int(os.environ.get('SSH_PORT', 22))  # Puerto SSH predeterminado
SSH_PASSWORD = os.environ.get('SSH_PASSWORD')  # Contraseña SSH (si no usas clave)
print(SSH_KEY_PATH, SSH_USER, SSH_PORT, SSH_PASSWORD)
# Lista de servicios permitidos para gestionar
ALLOWED_SERVICES = ['kiosk', 'videoloop']
logger = logging.getLogger(__name__)

# Verificar si las variables críticas están definidas
if not SSH_USER:
    logger.warning("SSH_USER no está definido en las variables de entorno. Se usará un valor predeterminado.")
    SSH_USER = 'pi'  # Valor predeterminado para Raspberry Pi
    
if not SSH_PASSWORD:
    logger.warning("SSH_PASSWORD no está definido en las variables de entorno.")
    
logger = logging.getLogger(__name__)

async def validate_ssh_credentials(device_id):
    """
    Verifica que se tienen las credenciales SSH necesarias para un dispositivo
    Intenta primero con WiFi, si falla intenta con LAN
    
    Args:
        device_id (str): ID del dispositivo
        
    Returns:
        dict: Resultado de la validación
    """
    db = SessionLocal()
    try:
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if not device:
            return {'success': False, 'message': 'Dispositivo no encontrado'}
        
        if not device.is_active:
            return {'success': False, 'message': 'El dispositivo no está activo'}
        
        # Probar conexión SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Lista de IPs para intentar, primero WiFi, luego LAN
        ip_addresses = []
        if device.ip_address_wifi:
            ip_addresses.append(('WiFi', device.ip_address_wifi))
        if device.ip_address_lan:
            ip_addresses.append(('LAN', device.ip_address_lan))
        
        if not ip_addresses:
            return {'success': False, 'message': 'No hay direcciones IP disponibles para conectar'}
        
        # Intentar cada IP hasta que una funcione
        connection_errors = []
        for connection_type, ip_address in ip_addresses:
            try:
                logger.info(f"Intentando conectar vía SSH a {connection_type} ({ip_address})")
                
                # Intentar conectar con clave SSH primero
                if os.path.exists(SSH_KEY_PATH):
                    key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
                    ssh.connect(ip_address, port=SSH_PORT,username=SSH_USER, pkey=key, timeout=5)
                else:
                    # Si no hay clave, usar contraseña
                    ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=5)
                
                # Si llegamos aquí, la conexión fue exitosa
                logger.info(f"Conexión SSH exitosa a {connection_type} ({ip_address})")
                
                # Probar si podemos usar sudo
                stdin, stdout, stderr = ssh.exec_command('echo "%s" | sudo -S echo "OK"' % SSH_PASSWORD)
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                
                # Cerrar conexión SSH
                ssh.close()
                
                if 'OK' in output:
                    return {
                        'success': True, 
                        'message': f'Credenciales SSH válidas con permisos sudo (vía {connection_type})',
                        'connection_type': connection_type,
                        'ip_address': ip_address
                    }
                else:
                    return {
                        'success': False, 
                        'message': f'Conexión SSH exitosa a {connection_type} ({ip_address}), pero sin permisos sudo: {error}',
                    }
                    
            except Exception as e:
                # Registrar el error y continuar con la siguiente IP
                error_msg = f"Error al conectar por SSH a {connection_type} ({ip_address}): {str(e)}"
                logger.warning(error_msg)
                connection_errors.append(error_msg)
                continue
        
        # Si llegamos aquí, ninguna conexión funcionó
        error_details = "\n".join(connection_errors)
        logger.error(f"No se pudo establecer conexión SSH con ninguna interfaz: {error_details}")
        return {'success': False, 'message': f'Error de conexión SSH a todas las interfaces disponibles'}
        
    finally:
        db.close()

async def manage_service(device_id, service_name, action):
    """
    Gestiona un servicio en el dispositivo remoto usando SSH.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a gestionar
        action (str): Acción a realizar: start, stop, restart, enable, disable, status
    
    Returns:
        dict: Resultado de la operación
    """
    # Validar que el servicio está en la lista de permitidos
    if service_name.lower() not in ALLOWED_SERVICES:
        return {'success': False, 'message': f'Servicio no permitido. Los servicios permitidos son: {", ".join(ALLOWED_SERVICES)}'}
    
    # Validar la acción
    valid_actions = ['start', 'stop', 'restart', 'enable', 'disable', 'status']
    if action.lower() not in valid_actions:
        return {'success': False, 'message': f'Acción no válida. Las acciones permitidas son: {", ".join(valid_actions)}'}
    
    db = SessionLocal()
    try:
        # Buscar el dispositivo en la base de datos
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if not device:
            return {'success': False, 'message': 'Dispositivo no encontrado'}
        
        if not device.is_active:
            return {'success': False, 'message': 'El dispositivo no está activo'}
        
        # Primero validar credenciales para determinar la mejor interfaz para conectar
        ssh_validation = await validate_ssh_credentials(device_id)
        if not ssh_validation['success']:
            return {'success': False, 'message': f'Error de validación SSH: {ssh_validation["message"]}'}
        
        # Usar la interfaz que funcionó en la validación
        connection_type = ssh_validation.get('connection_type', 'LAN')
        ip_address = ssh_validation.get('ip_address', device.ip_address_lan or device.ip_address_wifi)
        
        logger.info(f"Gestionando servicio {service_name} ({action}) vía {connection_type} ({ip_address})")
        
        # Conectar al dispositivo vía SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Usar la misma conexión que funcionó en la validación
            if os.path.exists(SSH_KEY_PATH):
                key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, pkey=key, timeout=10)
            else:
                # Si no hay clave, usar contraseña
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=10)
            
            # Ejecutar el comando según la acción solicitada
            if action == 'status':
                command = f'sudo systemctl status {service_name}'
            else:
                command = f'sudo systemctl {action} {service_name}'
            
            # Ejecutar comando
            stdin, stdout, stderr = ssh.exec_command(command)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            # Verificar el resultado
            if error and 'sudo' in error.lower():
                return {'success': False, 'message': f'Error de permisos sudo: {error}'}
            
            # Para las acciones de inicio/parada/reinicio, verificar el estado después
            if action in ['start', 'stop', 'restart']:
                status_command = f'sudo systemctl is-active {service_name}'
                stdin, stdout, stderr = ssh.exec_command(status_command)
                status = stdout.read().decode().strip()
                
                # También obtener más información del servicio
                stdin, stdout, stderr = ssh.exec_command(f'sudo systemctl status {service_name} | head -n 20')
                details = stdout.read().decode().strip()
                
                # Verificar si el servicio está en el estado esperado después de la acción
                expected_status = 'active' if action in ['start', 'restart'] else 'inactive'
                success = status == expected_status
                
                result = {
                    'success': success,
                    'message': f'Servicio {service_name} {action} completado. Estado actual: {status}',
                    'status': status,
                    'details': details
                }
            elif action in ['enable', 'disable']:
                # Verificar si el servicio está habilitado/deshabilitado
                status_command = f'sudo systemctl is-enabled {service_name}'
                stdin, stdout, stderr = ssh.exec_command(status_command)
                status = stdout.read().decode().strip()
                
                expected_status = 'enabled' if action == 'enable' else 'disabled'
                success = status == expected_status
                
                result = {
                    'success': success,
                    'message': f'Servicio {service_name} {action} completado. Estado: {status}',
                    'enabled': status
                }
            else:  # status
                result = {
                    'success': True,
                    'message': f'Estado del servicio {service_name}',
                    'output': output
                }
            
            # Cerrar conexión SSH
            ssh.close()
            
            # Actualizar el estado del servicio en la base de datos si corresponde
            if action in ['start', 'stop', 'restart'] and service_name == 'videoloop':
                device.videoloop_status = 'running' if result['status'] == 'active' else 'stopped'
                db.commit()
            elif action in ['start', 'stop', 'restart'] and service_name == 'kiosk':
                device.kiosk_status = 'running' if result['status'] == 'active' else 'stopped'
                db.commit()
            
            # Devolver resultado
            return result
            
        except Exception as e:
            logger.error(f"Error al gestionar servicio {service_name} ({action}): {str(e)}")
            return {'success': False, 'message': f'Error al ejecutar comando: {str(e)}'}
        
    finally:
        db.close()

async def restart_service(device_id, service_name):
    """
    Reinicia un servicio en el dispositivo remoto.
    Es un wrapper alrededor de manage_service para mantener compatibilidad.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a reiniciar
    
    Returns:
        dict: Resultado de la operación
    """
    return await manage_service(device_id, service_name, 'restart')

async def stop_service(device_id, service_name):
    """
    Detiene un servicio en el dispositivo remoto.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a detener
    
    Returns:
        dict: Resultado de la operación
    """
    return await manage_service(device_id, service_name, 'stop')

async def start_service(device_id, service_name):
    """
    Inicia un servicio en el dispositivo remoto.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a iniciar
    
    Returns:
        dict: Resultado de la operación
    """
    return await manage_service(device_id, service_name, 'start')

async def enable_service(device_id, service_name):
    """
    Habilita un servicio para que se inicie con el sistema.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a habilitar
    
    Returns:
        dict: Resultado de la operación
    """
    return await manage_service(device_id, service_name, 'enable')

async def disable_service(device_id, service_name):
    """
    Deshabilita un servicio para que no se inicie con el sistema.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a deshabilitar
    
    Returns:
        dict: Resultado de la operación
    """
    return await manage_service(device_id, service_name, 'disable')

async def get_service_status(device_id, service_name):
    """
    Obtiene el estado de un servicio.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a consultar
    
    Returns:
        dict: Resultado de la operación con el estado del servicio
    """
    return await manage_service(device_id, service_name, 'status')

# Endpoints para la API

@router.post("/{device_id}/service/{service_name}/{action}")
async def manage_device_service(
    device_id: str, 
    service_name: str, 
    action: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint para gestionar un servicio en un dispositivo.
    
    Args:
        device_id: ID del dispositivo
        service_name: Nombre del servicio (kiosk o videoloop)
        action: Acción a realizar (start, stop, restart, enable, disable, status)
    
    Returns:
        dict: Resultado de la operación
    """
    # Validar que el servicio está permitido
    if service_name.lower() not in ALLOWED_SERVICES:
        raise HTTPException(status_code=400, detail=f"Servicio no permitido. Servicios válidos: {', '.join(ALLOWED_SERVICES)}")
    
    # Validar que la acción está permitida
    valid_actions = ['start', 'stop', 'restart', 'enable', 'disable', 'status']
    if action.lower() not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Acción no válida. Acciones válidas: {', '.join(valid_actions)}")
    
    # Ejecutar la acción
    result = await manage_service(device_id, service_name, action)
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['message'])
    
    return result

@router.get("/devices/{device_id}/screenshot")
async def get_device_screenshot(device_id: str, db: Session = Depends(get_db)):
    """
    Obtiene una captura de pantalla del dispositivo remoto.
    Consume el endpoint API del cliente para capturar la pantalla.
    Primero intenta con la IP LAN, y si falla, prueba con la IP WiFi.
    """
    try:
        # Buscar el dispositivo en la base de datos
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if device is None:
            logger.error(f"Dispositivo no encontrado: {device_id}")
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        
        # Verificar si el dispositivo está activo
        if not device.is_active:
            logger.error(f"El dispositivo {device_id} no está activo")
            raise HTTPException(status_code=400, detail="El dispositivo no está activo")
        
        # Verificar que al menos una dirección IP está disponible
        if not device.ip_address_lan and not device.ip_address_wifi:
            logger.error(f"No se encontró ninguna dirección IP para el dispositivo {device_id}")
            raise HTTPException(
                status_code=400, 
                detail="No se encontró ninguna dirección IP para el dispositivo"
            )
        
        # Lista de IPs para intentar, primero LAN, luego WiFi
        ip_addresses = []
        if device.ip_address_wifi:
            ip_addresses.append(('WLAN', device.ip_address_wifi))
        if device.ip_address_wifi:
            ip_addresses.append(('LAN', device.ip_address_lan))
        
        # Intentar capturar la pantalla utilizando cada IP disponible
        last_error = None
        
        for connection_type, ip_address in ip_addresses:
            try:
                # URL del endpoint de captura de pantalla en el cliente
                screenshot_url = f"http://{ip_address}:8000/api/screenshot"
                
                logger.info(f"Intentando captura de pantalla vía {connection_type} ({ip_address}) desde {screenshot_url}")
                
                # Realizar la solicitud al cliente con un timeout reducido
                response = requests.get(screenshot_url, timeout=5)
                
                if response.status_code == 200:
                    logger.info(f"Captura de pantalla exitosa vía {connection_type} ({ip_address})")
                    
                    # Obtener el contenido de la imagen
                    image_content = response.content
                    
                    # Devolver la imagen directamente
                    return Response(
                        content=image_content,
                        media_type="image/png",
                        headers={
                            "Content-Disposition": f"inline; filename=screenshot-{device.name}.png"
                        }
                    )
                else:
                    logger.warning(f"Error al obtener captura desde {connection_type} ({ip_address}): {response.status_code}")
                    last_error = f"Error en {connection_type}: código {response.status_code}"
                    # Continuar con la siguiente IP
                    
            except requests.RequestException as e:
                logger.warning(f"Error de conexión con {connection_type} ({ip_address}): {str(e)}")
                last_error = f"Error de conexión con {connection_type}: {str(e)}"
                # Continuar con la siguiente IP
        
        # Si llegamos aquí, ninguna conexión funcionó
        logger.error(f"No se pudo obtener captura de pantalla de ninguna interfaz. Último error: {last_error}")
        raise HTTPException(
            status_code=500, 
            detail=f"No se pudo obtener la captura de pantalla: {last_error}"
        )
            
    except HTTPException:
        # Re-lanzar excepciones HTTPException
        raise
    except Exception as e:
        logger.exception(f"Error al procesar la solicitud de captura: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/devices/{device_id}/screenshot/file")
async def get_device_screenshot_as_file(device_id: str, db: Session = Depends(get_db)):
    """
    Obtiene una captura de pantalla del dispositivo remoto y la devuelve como un archivo descargable.
    Este método utiliza archivos temporales.
    """
    try:
        # Buscar el dispositivo en la base de datos
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if device is None:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        
        # Verificar si el dispositivo está activo
        if not device.is_active:
            raise HTTPException(status_code=400, detail="El dispositivo no está activo")
        
        # Obtener dirección IP del dispositivo
        device_ip = device.ip_address_lan or device.ip_address_wifi
        if not device_ip:
            raise HTTPException(
                status_code=400, 
                detail="No se encontró una dirección IP válida para el dispositivo"
            )
        
        # URL del endpoint de captura de pantalla en el cliente
        screenshot_url = f"http://{device_ip}:8000/api/screenshot/"
        
        # Realizar la solicitud al cliente
        try:
            response = requests.get(screenshot_url, timeout=10)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error al obtener captura desde el cliente: {response.status_code}"
                )
            
            # Crear un archivo temporal para la imagen
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            # Función para eliminar el archivo temporal después de enviarlo
            def cleanup():
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            # Devolver el archivo
            return FileResponse(
                path=temp_path,
                filename=f"screenshot-{device.name}.png",
                media_type="image/png",
                background=BackgroundTasks(cleanup)  # Usar la función de limpieza
            )
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error al conectar con el dispositivo: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error al procesar la solicitud de captura: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")