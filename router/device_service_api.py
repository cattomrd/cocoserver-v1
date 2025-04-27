from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import requests
import logging
from datetime import datetime
import traceback

from models import models, schemas
from models.database import get_db

from utils.helpers import manage_service   

# Configuración del logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/device-services",
    tags=["device-services"]
)

# Lista de servicios permitidos
ALLOWED_SERVICES = ['videoloop', 'kiosk']

# Lista de acciones permitidas
VALID_ACTIONS = ['start', 'stop', 'restart', 'enable', 'disable', 'status']

async def manage_service_via_api(device_id: str, service_name: str, action: str, db: Session) -> Dict[str, Any]:
    """
    Gestiona un servicio en un dispositivo remoto a través de su API local
    
    Args:
        device_id (str): ID del dispositivo
        service_name (str): Nombre del servicio a gestionar (videoloop, kiosk)
        action (str): Acción a realizar (start, stop, restart, enable, disable, status)
        db (Session): Sesión de base de datos
    
    Returns:
        Dict[str, Any]: Resultado de la operación
    """
    # Validar servicio
    if service_name not in ALLOWED_SERVICES:
        raise HTTPException(
            status_code=400, 
            detail=f"Servicio no permitido. Los servicios permitidos son: {', '.join(ALLOWED_SERVICES)}"
        )
    
    # Validar acción
    if action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Acción no válida. Las acciones permitidas son: {', '.join(VALID_ACTIONS)}"
        )
    
    # Buscar el dispositivo en la base de datos
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Verificar que el dispositivo está activo
    if not device.is_active:
        return {
            "success": False,
            "message": "El dispositivo no está activo. Verifique su conexión.",
            "status": "unknown",
            "timestamp": datetime.now().isoformat()
        }
    
    # Obtener la dirección IP del dispositivo (preferir LAN sobre WiFi)
    device_ip = device.ip_address_lan or device.ip_address_wifi
    if not device_ip:
        return {
            "success": False,
            "message": "El dispositivo no tiene una dirección IP configurada.",
            "status": "unknown",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # Construir la URL para la API del cliente
        api_url = f"http://{device_ip}:8000/services/{service_name}/{action}"
        logger.info(f"Enviando comando {action} al servicio {service_name} en dispositivo {device_id} ({device_ip})")
        
        # Realizar la petición al cliente
        response = requests.get(api_url, timeout=10)
        
        # Procesar la respuesta
        if response.status_code != 200:
            logger.error(f"Error en la respuesta API: {response.status_code} - {response.text}")
            return {
                "success": False,
                "message": f"Error en la respuesta del dispositivo: {response.status_code}",
                "details": response.text,
                "timestamp": datetime.now().isoformat()
            }
        
        # Verificar el contenido de la respuesta
        result = response.text.strip()
        
        # Actualizar el estado en la base de datos si la acción fue exitosa
        # y si estamos iniciando, deteniendo o reiniciando un servicio
        if result == "success" and action in ["start", "stop", "restart"]:
            # Obtener el estado actual después de la acción
            status_url = f"http://{device_ip}:8000/services/{service_name}/status"
            try:
                status_response = requests.get(status_url, timeout=5)
                if status_response.status_code == 200:
                    # Verificar si está activo o detenido
                    status_result = status_response.text.strip()
                    is_running = status_result == "running" or "active" in status_result
                    
                    # Actualizar en la base de datos
                    if service_name == "videoloop":
                        device.videoloop_status = "running" if is_running else "stopped"
                    elif service_name == "kiosk":
                        device.kiosk_status = "running" if is_running else "stopped"
                    
                    db.commit()
                    logger.info(f"Estado de {service_name} actualizado a: {'running' if is_running else 'stopped'}")
            except Exception as status_error:
                logger.error(f"Error al obtener estado actualizado: {str(status_error)}")
        
        # Obtener estado para verificar si está habilitado
        enabled_status = "unknown"
        if result == "success" and action in ["enable", "disable", "status"]:
            try:
                enabled_url = f"http://{device_ip}:8000/services/{service_name}/is-enabled"
                enabled_response = requests.get(enabled_url, timeout=5)
                if enabled_response.status_code == 200:
                    enabled_result = enabled_response.text.strip()
                    enabled_status = enabled_result
            except Exception as enabled_error:
                logger.error(f"Error al obtener estado de habilitación: {str(enabled_error)}")
        
        # Construir respuesta detallada
        response_data = {
            "success": result == "success",
            "message": f"Acción {action} ejecutada {'correctamente' if result == 'success' else 'con errores'} en el servicio {service_name}",
            "details": result if result != "success" else f"El servicio {service_name} ha sido {action}ado correctamente",
            "service": service_name,
            "action": action,
            "status": "running" if device.videoloop_status == "running" else "stopped" if service_name == "videoloop" else 
                    "running" if device.kiosk_status == "running" else "stopped",
            "enabled": enabled_status,
            "timestamp": datetime.now().isoformat()
        }
        
        return response_data
        
    except requests.RequestException as e:
        logger.error(f"Error de conexión con el dispositivo {device_id}: {str(e)}")
        return {
            "success": False,
            "message": f"No se pudo conectar con el dispositivo: {str(e)}",
            "status": "unknown",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error al gestionar servicio: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"Error interno: {str(e)}",
            "status": "unknown",
            "timestamp": datetime.now().isoformat()
        }

@router.post("/{device_id}/{service_name}/{action}")
async def service_management_endpoint(
    device_id: str,
    service_name: str,
    action: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint para gestionar servicios en dispositivos remotos vía API.
    
    Args:
        device_id: ID del dispositivo
        service_name: Nombre del servicio (videoloop, kiosk)
        action: Acción a realizar (start, stop, restart, enable, disable, status)
    
    Returns:
        Dict: Resultado de la operación
    """
    return await manage_service_via_api(device_id, service_name, action, db)

# Endpoints adicionales útiles

@router.get("/{device_id}/services")
async def list_device_services(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de servicios disponibles en un dispositivo y su estado
    """
    # Buscar el dispositivo en la base de datos
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Verificar que el dispositivo está activo
    if not device.is_active:
        return {
            "success": False,
            "message": "El dispositivo no está activo. Verifique su conexión.",
            "services": []
        }
    
    # Obtener la dirección IP del dispositivo
    device_ip = device.ip_address_lan or device.ip_address_wifi
    if not device_ip:
        return {
            "success": False,
            "message": "El dispositivo no tiene una dirección IP configurada.",
            "services": []
        }
    
    # Obtener servicios y su estado
    services_data = []
    for service_name in ALLOWED_SERVICES:
        try:
            # Obtener estado actual
            status_url = f"http://{device_ip}:8000/services/{service_name}/status"
            status_response = requests.get(status_url, timeout=5)
            status = status_response.text.strip() if status_response.status_code == 200 else "unknown"
            
            # Obtener si está habilitado
            enabled_url = f"http://{device_ip}:8000/services/{service_name}/is-enabled"
            enabled_response = requests.get(enabled_url, timeout=5)
            enabled = enabled_response.text.strip() if enabled_response.status_code == 200 else "unknown"
            
            services_data.append({
                "name": service_name,
                "status": status,
                "enabled": enabled,
                "actions": VALID_ACTIONS
            })
        except Exception as e:
            logger.error(f"Error al obtener información del servicio {service_name}: {str(e)}")
            services_data.append({
                "name": service_name,
                "status": "error",
                "enabled": "unknown",
                "error": str(e),
                "actions": VALID_ACTIONS
            })
    
    return {
        "success": True,
        "device_id": device_id,
        "device_name": device.name,
        "services": services_data
    }