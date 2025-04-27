# router/services_enhanced.py
import tempfile
from fastapi import APIRouter, Request, Depends, HTTPException, Response, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
import requests
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, Union, List
import httpx
import asyncio
import os
import paramiko
import logging
from datetime import datetime

from utils import ssh_helper
from models import models
from models.database import SessionLocal, get_db

router = APIRouter(
    prefix="/services",
    tags=["services"]
)

# Lista de servicios permitidos
ALLOWED_SERVICES = ['videoloop', 'kiosk']

# Obtener variables de entorno para SSH
SSH_USERNAME = os.environ.get('SSH_USER')
SSH_PASSWORD = os.environ.get('SSH_PASSWORD')
logger = logging.getLogger(__name__)

# Tiempo de espera para API y SSH en segundos
API_TIMEOUT = 5.0
SSH_TIMEOUT = 10.0

async def manage_service_via_api(ip_address: str, service_name: str, action: str) -> Dict[str, Any]:
    """
    Gestiona un servicio en el dispositivo remoto usando su API.
    
    Args:
        ip_address (str): Dirección IP del dispositivo
        service_name (str): Nombre del servicio a gestionar
        action (str): Acción a realizar: start, stop, restart, status
    
    Returns:
        dict: Resultado de la operación
    """
    if service_name not in ALLOWED_SERVICES:
        return {
            'success': False, 
            'message': f'Servicio no permitido: {service_name}. Los servicios permitidos son: {", ".join(ALLOWED_SERVICES)}'
        }
    
    valid_actions = ['start', 'stop', 'restart', 'status']
    if action not in valid_actions:
        return {
            'success': False, 
            'message': f'Acción no válida: {action}. Las acciones permitidas son: {", ".join(valid_actions)}'
        }
    
    try:
        # Construir URL para la API del cliente
        api_url = f"http://{ip_address}:8000/{service_name}/{action}"
        logger.info(f"Intentando manejar servicio {service_name} ({action}) vía API: {api_url}")
        
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(api_url)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Error de API: Status code {response.status_code}',
                    'details': response.text
                }
            
            result_text = response.text.strip()
            
            # Interpretar la respuesta
            if result_text == "success":
                # Determinar estado basado en la acción
                state = None
                if action == 'start' or action == 'restart':
                    state = 'running'
                elif action == 'stop':
                    state = 'stopped'
                
                return {
                    'success': True,
                    'message': f'Servicio {service_name} {action} completado exitosamente',
                    'status': state,
                    'method': 'api'
                }
            else:
                # Si la respuesta contiene "error:", es un mensaje de error
                return {
                    'success': False,
                    'message': f'Error al {action} servicio {service_name}',
                    'details': result_text,
                    'method': 'api'
                }
    
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        logger.warning(f"No se pudo conectar a la API del dispositivo: {str(e)}")
        return {
            'success': False,
            'message': f'No se pudo conectar a la API: {str(e)}',
            'error_type': 'connection'
        }
    except Exception as e:
        logger.error(f"Error al manejar servicio vía API: {str(e)}")
        return {
            'success': False,
            'message': f'Error al llamar a la API: {str(e)}',
            'error_type': 'general'
        }

async def validate_ssh_credentials(device_id: str) -> Dict[str, Any]:
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
                    ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, pkey=key, timeout=SSH_TIMEOUT)
                else:
                    # Si no hay clave, usar contraseña
                    ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=SSH_TIMEOUT)
                
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

async def manage_service_via_ssh(device_id: str, service_name: str, action: str) -> Dict[str, Any]:
    """
    Gestiona un servicio en el dispositivo remoto usando SSH (método de fallback).
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a gestionar
        action (str): Acción a realizar: start, stop, restart, enable, disable, status
    
    Returns:
        dict: Resultado de la operación
    """
    # Validar que el servicio está en la lista de permitidos
    if service_name.lower() not in ALLOWED_SERVICES:
        return {
            'success': False, 
            'message': f'Servicio no permitido. Los servicios permitidos son: {", ".join(ALLOWED_SERVICES)}'
        }
    
    # Validar la acción
    valid_actions = ['start', 'stop', 'restart', 'enable', 'disable', 'status']
    if action.lower() not in valid_actions:
        return {
            'success': False, 
            'message': f'Acción no válida. Las acciones permitidas son: {", ".join(valid_actions)}'
        }
    
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
            return {
                'success': False, 
                'message': f'Error de validación SSH: {ssh_validation["message"]}'
            }
        
        # Usar la interfaz que funcionó en la validación
        connection_type = ssh_validation.get('connection_type', 'LAN')
        ip_address = ssh_validation.get('ip_address', device.ip_address_lan or device.ip_address_wifi)
        
        logger.info(f"Gestionando servicio {service_name} ({action}) vía SSH {connection_type} ({ip_address})")
        
        # Conectar al dispositivo vía SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Usar la misma conexión que funcionó en la validación
            if os.path.exists(SSH_KEY_PATH):
                key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, pkey=key, timeout=SSH_TIMEOUT)
            else:
                # Si no hay clave, usar contraseña
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=SSH_TIMEOUT)
            
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
                return {
                    'success': False, 
                    'message': f'Error de permisos sudo: {error}',
                    'method': 'ssh'
                }
            
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
                    'status': 'running' if status == 'active' else 'stopped',
                    'details': details,
                    'method': 'ssh'
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
                    'enabled': status,
                    'method': 'ssh'
                }
            else:  # status
                result = {
                    'success': True,
                    'message': f'Estado del servicio {service_name}',
                    'output': output,
                    'method': 'ssh'
                }
            
            # Cerrar conexión SSH
            ssh.close()
            return result
            
        except Exception as e:
            logger.error(f"Error al gestionar servicio {service_name} ({action}): {str(e)}")
            return {
                'success': False, 
                'message': f'Error al ejecutar comando SSH: {str(e)}',
                'method': 'ssh'
            }
        
    finally:
        db.close()

async def manage_service(device_id: str, service_name: str, action: str) -> Dict[str, Any]:
    """
    Gestiona un servicio en el dispositivo remoto.
    Primero intenta vía API, y si falla, usa SSH como fallback.
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a gestionar
        action (str): Acción a realizar: start, stop, restart, status
    
    Returns:
        dict: Resultado de la operación
    """
    # Buscar el dispositivo en la base de datos
    db = SessionLocal()
    try:
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if not device:
            return {'success': False, 'message': 'Dispositivo no encontrado'}
        
        if not device.is_active:
            return {'success': False, 'message': 'El dispositivo no está activo'}
        
        # Obtener IPs del dispositivo
        ip_address = device.ip_address_lan or device.ip_address_wifi
        if not ip_address:
            return {'success': False, 'message': 'No hay direcciones IP disponibles para conectar'}
        
        # Primer intento: usar API
        result = await manage_service_via_api(ip_address, service_name, action)
        
        # Si la API falló por problema de conexión, intentar con SSH como fallback
        if not result['success'] and result.get('error_type') == 'connection':
            logger.info(f"API falló, intentando vía SSH como fallback para {service_name} ({action})")
            result = await manage_service_via_ssh(device_id, service_name, action)
        
        # Actualizar el estado del servicio en la base de datos si corresponde
        if result['success'] and action in ['start', 'stop', 'restart'] and 'status' in result:
            if service_name == 'videoloop':
                device.videoloop_status = result['status']
            elif service_name == 'kiosk':
                device.kiosk_status = result['status']
            db.commit()
        
        return result
        
    finally:
        db.close()

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
        raise HTTPException(
            status_code=400, 
            detail=f"Servicio no permitido. Servicios válidos: {', '.join(ALLOWED_SERVICES)}"
        )
    
    # Validar que la acción está permitida
    valid_actions = ['start', 'stop', 'restart', 'enable', 'disable', 'status']
    if action.lower() not in valid_actions:
        raise HTTPException(
            status_code=400, 
            detail=f"Acción no válida. Acciones válidas: {', '.join(valid_actions)}"
        )
    
    # Buscar el dispositivo
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Ejecutar la acción
    result = await manage_service(device_id, service_name, action)
    
    if not result['success']:
        if 'No se pudo conectar' in result['message']:
            # Error de conexión (400 Bad Request)
            raise HTTPException(status_code=400, detail=result['message'])
        else:
            # Error al ejecutar la acción (500 Internal Server Error)
            raise HTTPException(status_code=500, detail=result['message'])
    
    return result

@router.get("/devices/{device_id}/screenshot")
async def get_device_screenshot(device_id: str, db: Session = Depends(get_db)):
    """
    Obtiene una captura de pantalla del dispositivo remoto.
    Consume el endpoint API del cliente para capturar la pantalla.
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
        
        # Obtener dirección IP del dispositivo (preferiblemente LAN)
        device_ip = device.ip_address_lan or device.ip_address_wifi
        if not device_ip:
            logger.error(f"No se encontró una dirección IP válida para el dispositivo {device_id}")
            raise HTTPException(
                status_code=400, 
                detail="No se encontró una dirección IP válida para el dispositivo"
            )
        
        # URL del endpoint de captura de pantalla en el cliente
        screenshot_url = f"http://{device_ip}:8000/api/screenshot/"
        
        logger.info(f"Solicitando captura de pantalla desde {screenshot_url}")
        
        # Realizar la solicitud al cliente
        try:
            # Configurar timeout para evitar esperas largas
            response = requests.get(screenshot_url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Error al obtener captura desde el cliente: {response.status_code}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error al obtener captura desde el cliente: {response.status_code}"
                )
                
            # Obtener el contenido de la imagen
            image_content = response.content
            
            # Método directo: devolver la imagen directamente
            return Response(
                content=image_content,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"inline; filename=screenshot-{device.name}.png"
                }
            )
            
        except requests.RequestException as e:
            logger.error(f"Error de conexión con el cliente: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error al conectar con el dispositivo: {str(e)}"
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