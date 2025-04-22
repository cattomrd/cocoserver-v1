# app/utils/ping_checker.py
import subprocess
import platform
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from models import models
from models.database import SessionLocal

logger = logging.getLogger(__name__)

async def ping_host(ip_address):
    """
    Verifica si un host está activo mediante ping
    
    Args:
        ip_address (str): Dirección IP del host a verificar
        
    Returns:
        bool: True si el host está activo, False si no
    """
    if not ip_address:
        return False
        
    # Comando ping diferente según el sistema operativo
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip_address]
    
    try:
        # Ejecutar comando ping con timeout
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3)
        
        # Comprobar si el ping tuvo éxito
        return process.returncode == 0
    except (asyncio.TimeoutError, subprocess.SubprocessError):
        return False
    except Exception as e:
        logger.error(f"Error al hacer ping a {ip_address}: {str(e)}")
        return False

async def check_device_status(device_id=None):
    """
    Verifica el estado de los dispositivos probando ambas interfaces (LAN y WiFi)
    
    Args:
        device_id (str, optional): ID del dispositivo a verificar. Si es None, verifica todos.
        
    Returns:
        dict: Resultados de la verificación {device_id: is_active}
    """
    db = SessionLocal()
    try:
        results = {}
        
        if device_id:
            # Verificar solo un dispositivo específico
            device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
            if device:
                # Intentar ping a LAN primero
                lan_active = await ping_host(device.ip_address_lan)
                
                # Si LAN falla, intentar WiFi
                wifi_active = False
                if not lan_active and device.ip_address_wifi:
                    wifi_active = await ping_host(device.ip_address_wifi)
                
                # Dispositivo activo si cualquiera de las interfaces responde
                is_active = lan_active or wifi_active
                
                # Actualizar el estado del dispositivo
                device.is_active = is_active
                if is_active:
                    # Actualizar la marca de tiempo de última conexión
                    device.last_seen = datetime.now()
                db.commit()
                
                # Guardar resultado específico de cada interfaz para logs
                results[device.device_id] = {
                    'is_active': is_active,
                    'lan_active': lan_active,
                    'wifi_active': wifi_active
                }
                
                # Log para debugging
                logger.info(f"Dispositivo {device.name} ({device.device_id}): " +
                        f"LAN ({device.ip_address_lan}): {'OK' if lan_active else 'FAIL'}, " +
                        f"WiFi ({device.ip_address_wifi}): {'OK' if wifi_active else 'FAIL'}, " +
                        f"Estado: {'Activo' if is_active else 'Inactivo'}")
        else:
            # Verificar todos los dispositivos
            devices = db.query(models.Device).all()
            for device in devices:
                # Intentar ping a LAN primero
                lan_active = await ping_host(device.ip_address_lan)
                
                # Si LAN falla, intentar WiFi
                wifi_active = False
                if not lan_active and device.ip_address_wifi:
                    wifi_active = await ping_host(device.ip_address_wifi)
                
                # Dispositivo activo si cualquiera de las interfaces responde
                is_active = lan_active or wifi_active
                
                # Actualizar el estado del dispositivo
                device.is_active = is_active
                if is_active:
                    # Actualizar la marca de tiempo de última conexión
                    device.last_seen = datetime.now()
                
                # Guardar resultado específico de cada interfaz para logs
                results[device.device_id] = {
                    'is_active': is_active,
                    'lan_active': lan_active,
                    'wifi_active': wifi_active
                }
                
                # Log para debugging
                logger.info(f"Dispositivo {device.name} ({device.device_id}): " +
                        f"LAN ({device.ip_address_lan}): {'OK' if lan_active else 'FAIL'}, " +
                        f"WiFi ({device.ip_address_wifi}): {'OK' if wifi_active else 'FAIL'}, " +
                        f"Estado: {'Activo' if is_active else 'Inactivo'}")
            
            db.commit()
            
        return results
    finally:
        db.close()

async def periodic_check_devices(interval_minutes=5):
    """
    Ejecuta la verificación periódica de dispositivos
    
    Args:
        interval_minutes (int): Intervalo de verificación en minutos
    """
    while True:
        try:
            logger.info("Iniciando verificación periódica de dispositivos")
            results = await check_device_status()
            
            # Contar dispositivos activos e inactivos
            active_count = sum(1 for result in results.values() if result['is_active'])
            inactive_count = len(results) - active_count
            
            # Contar conexiones por tipo de interfaz
            lan_active_count = sum(1 for result in results.values() if result['lan_active'])
            wifi_active_count = sum(1 for result in results.values() if result['wifi_active'])
            
            logger.info(f"Verificación completada. Dispositivos activos: {active_count}, inactivos: {inactive_count}")
            logger.info(f"Conexiones activas por LAN: {lan_active_count}, por WiFi: {wifi_active_count}")
        except Exception as e:
            logger.error(f"Error en la verificación periódica: {str(e)}")
        
        # Esperar el intervalo especificado
        await asyncio.sleep(interval_minutes * 60)

# Función para iniciar la verificación periódica desde main.py
def start_background_ping_checker(app):
    """
    Inicia el verificador de ping en segundo plano
    
    Args:
        app: Instancia de FastAPI
    """
    @app.on_event("startup")
    async def start_ping_checker():
        asyncio.create_task(periodic_check_devices())
    start_ping_checker()