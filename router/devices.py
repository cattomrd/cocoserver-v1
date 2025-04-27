# app/routers/devices.py
from tempfile import template
from fastapi import APIRouter, HTTPException, Depends, status, Form, Request, Query, Body # type: ignore
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse  # type: ignore
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session # type: ignore
from typing import List, Optional
from datetime import datetime
from models import models, schemas
from models.database import get_db
from utils.ping_checker import check_device_status, ping_host
from utils.hostname_changer import change_hostname, validate_ssh_credentials
import os
import logging
from fastapi.logger import logger # type: ignore
import requests
# Configuración del logger
logging.basicConfig(level=logging.INFO) 
router = APIRouter(
    prefix="/api/devices",
    tags=["devices"]
)

templates = Jinja2Templates(directory="templates")


@router.post("/", response_model=schemas.Device, status_code=status.HTTP_201_CREATED)
def register_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    db_device = db.query(models.Device).filter(models.Device.device_id == device.device_id).first()
    if db_device:
        raise HTTPException(status_code=400, detail="Device ID already registered")
    
    db_mac = db.query(models.Device).filter(models.Device.mac_address == device.mac_address).first()
    if db_mac:
        raise HTTPException(status_code=400, detail="MAC address already registered")
    
    # Crear el nuevo dispositivo con todos los campos
    new_device = models.Device(**device.dict())
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

@router.get("/", response_model=List[schemas.Device])
def get_devices(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(models.Device)
    if active_only:
        query = query.filter(models.Device.is_active == True)
    return query.offset(skip).limit(limit).all()

@router.get("/{device_id}", response_model=schemas.Device)
def get_device(device_id: str, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.put("/{device_id}", response_model=schemas.Device)
def update_device(device_id: str, device: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    db_device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if db_device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_data = device.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_device, key, value)
    
    db.commit()
    db.refresh(db_device)
    return db_device

@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: str, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.delete(device)
    db.commit()
    return {"status": "success"}

@router.post("/status", response_model=schemas.Device)
def update_device_status(status_update: schemas.DeviceStatus, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.device_id == status_update.device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Actualizar métricas
    device.cpu_temp = status_update.cpu_temp
    device.memory_usage = status_update.memory_usage
    device.disk_usage = status_update.disk_usage
    
    # Actualizar direcciones IP si se proporcionan
    if status_update.ip_address_lan is not None:
        device.ip_address_lan = status_update.ip_address_lan
        
    if status_update.ip_address_wifi is not None:
        device.ip_address_wifi = status_update.ip_address_wifi
    
    # Actualizar MAC de wlan0 si se proporciona
    if status_update.wlan0_mac is not None:
        device.wlan0_mac = status_update.wlan0_mac
    
    # Actualizar estados de servicios si se proporcionan
    if status_update.videoloop_status:
        device.videoloop_status = status_update.videoloop_status
    
    if status_update.kiosk_status:
        device.kiosk_status = status_update.kiosk_status
    
    db.commit()
    db.refresh(device)
    return device

# Endpoint para verificar el estado de un dispositivo mediante ping
@router.get("/{device_id}/ping", response_model=dict)
async def ping_device(device_id: str, db: Session = Depends(get_db)):
    """
    Verifica el estado de un dispositivo mediante ping a ambas interfaces (LAN y WiFi)
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Realizar ping a ambas interfaces y actualizar el estado
    result = await check_device_status(device_id=device_id)
    device_result = result.get(device_id, {})
    
    # Refrescar el dispositivo desde la base de datos después de la actualización
    db.refresh(device)
    
    # Preparar respuesta detallada
    response = {
        "device_id": device_id,
        "name": device.name,
        "is_active": device_result.get('is_active', device.is_active),
        "ip_address_lan": device.ip_address_lan,
        "ip_address_wifi": device.ip_address_wifi,
        "lan_active": device_result.get('lan_active', False),
        "wifi_active": device_result.get('wifi_active', False),
        "message": "Dispositivo activo" if device.is_active else "Dispositivo inactivo"
    }
    
    return response

# Endpoint para verificar el estado de todos los dispositivos
@router.get("/ping/all", response_model=dict)
async def ping_all_devices():
    """
    Verifica el estado de todos los dispositivos mediante ping a ambas interfaces
    """
    results = await check_device_status()
    
    # Contar dispositivos activos e inactivos
    active_count = sum(1 for result in results.values() if result['is_active'])
    inactive_count = len(results) - active_count
    
    # Contar conexiones por tipo de interfaz
    lan_active_count = sum(1 for result in results.values() if result['lan_active'])
    wifi_active_count = sum(1 for result in results.values() if result['wifi_active'])
    
    return {
        "results": results, 
        "total": len(results), 
        "active": active_count,
        "inactive": inactive_count,
        "lan_active": lan_active_count,
        "wifi_active": wifi_active_count
    }

# Endpoint para manejar servicios de los dispositivos
@router.post("/{device_id}/service/{service_name}/{action}", response_model=schemas.ServiceActionResponse)
async def manage_service(
    device_id: str, 
    service_name: str,
    action: str,
    db: Session = Depends(get_db)
):
    """
    Gestiona un servicio en el dispositivo (start, stop, restart, status)
    """
    # Validar servicio
    if service_name not in ["videoloop", "kiosk"]:
        raise HTTPException(status_code=400, detail=f"Servicio no soportado: {service_name}")
    
    # Validar acción
    if action not in ["start", "stop", "restart", "status"]:
        raise HTTPException(status_code=400, detail=f"Acción no válida: {action}")
    
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Implementación del manejo de servicios
    # Esta parte generalmente interactúa con el dispositivo remoto a través de su API
    # Para este ejemplo, simplemente devolvemos una respuesta simulada
    
    return schemas.ServiceActionResponse(
        device_id=device_id,
        action=action,
        service=service_name,
        success=True,
        message=f"Acción {action} ejecutada en servicio {service_name}",
        timestamp=datetime.now()
    )

# Endpoint para cambiar el hostname de un dispositivo
@router.post("/{device_id}/hostname", response_model=dict)
async def update_device_hostname(
    device_id: str, 
    new_hostname: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Cambia el hostname de un dispositivo Raspberry Pi
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Validar que el nuevo hostname es válido
    # Debe contener solo letras, números y guiones, sin espacios
    import re
    if not re.match(r'^[a-zA-Z0-9-]+$', new_hostname):
        raise HTTPException(
            status_code=400, 
            detail="El hostname solo puede contener letras, números y guiones"
        )
    
    # Verificar que el dispositivo está activo
    if not device.is_active:
        raise HTTPException(
            status_code=400, 
            detail="El dispositivo no está activo. Verifique la conexión antes de cambiar el hostname"
        )
    
    # Llamar a la función que implementa el cambio de hostname
    from utils.hostname_changer import change_hostname
    result = await change_hostname(device_id, new_hostname)
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['message'])
    
    return result
    

# Endpoint para validar credenciales SSH
@router.get("/{device_id}/ssh/validate", response_model=dict)
async def validate_device_ssh(device_id: str, db: Session = Depends(get_db)):
    """
    Verifica que se tienen las credenciales SSH necesarias para un dispositivo
    """
    try:
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Verificar credenciales SSH
        from utils.hostname_changer import validate_ssh_credentials
        result = await validate_ssh_credentials(device_id)
        
        return result
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return {"success": False, "message": f"Error interno del servidor: {str(e)}"}
    
@router.get("/{device_id}/logs", response_class=PlainTextResponse)
async def get_device_logs(
    device_id: str, 
    db: Session = Depends(get_db),
    lines: int = 500
):
    """
    Obtiene los logs del servicio para un dispositivo específico
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    ip_address = device.ip_address_lan or device.ip_address_wifi
    
    if ip_address:
        try:
            # Intentar obtener logs directamente del dispositivo
            url = f"http://{ip_address}:8000/api/logs?lines={lines}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                logs = response.text
                
                # Opcional: Actualizar los logs en la base de datos
                device.service_logs = logs
                db.commit()
                
                # Asegurar que los saltos de línea se preserven
                return PlainTextResponse(logs, media_type="text/plain; charset=utf-8")
            
            logger.warning(f"Error al obtener logs del dispositivo: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al dispositivo {device_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error al obtener logs del dispositivo: {str(e)}")


@router.get("/ui/devices", response_class=HTMLResponse)
async def list_devices(
    request: Request,
    active_only: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    search_field: Optional[str] = Query("all"),
    db: Session = Depends(get_db)
):
    # Convertir active_only a booleano
    is_active_only = active_only == "on"
    
    # Iniciar consulta
    query = db.query(models.Device)
    
    # Aplicar filtro de actividad si se seleccionó
    if is_active_only:
        query = query.filter(models.Device.is_active == True)
    
    # Aplicar filtro de búsqueda si existe un término
    if search:
        if search_field == 'name':
            query = query.filter(models.Device.name.ilike(f'%{search}%'))
        elif search_field == 'location':
            query = query.filter(models.Device.location.ilike(f'%{search}%'))
        elif search_field == 'tienda':
            query = query.filter(models.Device.tienda.ilike(f'%{search}%'))
        elif search_field == 'model':
            query = query.filter(models.Device.model.ilike(f'%{search}%'))
        elif search_field == 'ip':
            # Buscar en ambos campos de IP
            query = query.filter(or_(
                models.Device.ip_address_lan.ilike(f'%{search}%'),
                models.Device.ip_address_wifi.ilike(f'%{search}%')
            ))
        else:  # 'all' o cualquier otro valor
            # Buscar en todos los campos relevantes
            query = query.filter(or_(
                models.Device.name.ilike(f'%{search}%'),
                models.Device.location.ilike(f'%{search}%'),
                models.Device.tienda.ilike(f'%{search}%'),
                models.Device.model.ilike(f'%{search}%'),
                models.Device.ip_address_lan.ilike(f'%{search}%'),
                models.Device.ip_address_wifi.ilike(f'%{search}%')
            ))
    
    # Ejecutar la consulta
    devices = query.order_by(models.Device.name).all()
    
    # Renderizar la plantilla con los resultados y parámetros actuales
    return templates.TemplateResponse(
        "devices.html", 
        {
            "request": request,
            "devices": devices, 
            "active_only": is_active_only,
            "search_term": search,
            "search_field": search_field
        }
    )

@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def get_device_detail(
    request: Request, 
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Página de detalle de un dispositivo específico
    """
    # Realizar el query con join para cargar las playlists asociadas
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Cargar explícitamente las playlists del dispositivo
    device_playlists = db.query(models.Playlist).join(
        models.DevicePlaylist,
        models.DevicePlaylist.playlist_id == models.Playlist.id
    ).filter(
        models.DevicePlaylist.device_id == device_id
    ).all()
    
    # Asignar las playlists al dispositivo
    device.playlists = device_playlists
    
    # Obtener fecha actual para comparaciones en la plantilla
    from datetime import datetime
    now = datetime.now()
    
    # Intentar obtener el estado del servicio videoloop
    service_status = None
    if device.is_active:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{device.ip_address_lan or device.ip_address_wifi}:8000/service/videoloop/status")
                if response.status_code == 200:
                    service_status = response.json()
        except:
            # Si no se puede conectar, establecer estado como desconocido
            service_status = {"status": "unknown", "active": False, "enabled": False}
    
    return templates.TemplateResponse(
        "device_detail.html", 
        {
            "request": request, 
            "title": f"Dispositivo: {device.name}",
            "device": device,
            "service_status": service_status,
            "now": now  # Pasar la fecha actual a la plantilla
        }
    )