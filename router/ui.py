# Archivo app/routers/ui.py - Corregido para manejar la ruta de videos correctamente
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import sys
import os
from datetime import datetime
from sqlalchemy import or_

# Añadir la ruta del directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importaciones absolutas en lugar de relativas
from models import models, schemas
from models.database import get_db

router = APIRouter(
    prefix="/ui",
    tags=["ui"]
)

# Configurar templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Página principal del dashboard
    """
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Raspberry Pi Registry"})

@router.get("/devices", response_class=HTMLResponse)
async def get_devices_page(
    request: Request, 
    active_only: bool = False,
    search: Optional[str] = None,
    search_field: Optional[str] = "all",
    db: Session = Depends(get_db)
):
    """
    Página que muestra la lista de dispositivos registrados
    """
    # Consulta base con join a las playlists
    query = db.query(models.Device).outerjoin(
        models.DevicePlaylist,
        models.DevicePlaylist.device_id == models.Device.device_id
    ).outerjoin(
        models.Playlist,
        models.Playlist.id == models.DevicePlaylist.playlist_id
    )
    
    # Filtros adicionales
    if active_only:
        query = query.filter(models.Device.is_active == True)
    
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        if search_field == 'name':
            query = query.filter(models.Device.name.ilike(search_term))
        elif search_field == 'location':
            query = query.filter(models.Device.location.ilike(search_term))
        elif search_field == 'tienda':
            query = query.filter(models.Device.tienda.ilike(search_term))
        elif search_field == 'model':
            query = query.filter(models.Device.model.ilike(search_term))
        elif search_field == 'ip':
            query = query.filter(
                or_(
                    models.Device.ip_address_lan.ilike(search_term),
                    models.Device.ip_address_wifi.ilike(search_term)
                )
            )
        else:  # 'all'
            query = query.filter(
                or_(
                    models.Device.device_id.ilike(search_term),
                    models.Device.name.ilike(search_term),
                    models.Device.location.ilike(search_term),
                    models.Device.tienda.ilike(search_term),
                    models.Device.model.ilike(search_term),
                    models.Device.ip_address_lan.ilike(search_term),
                    models.Device.ip_address_wifi.ilike(search_term),
                    models.Playlist.title.ilike(search_term)
                )
            )
    
    # Es importante usar distinct() para evitar duplicados si un dispositivo tiene múltiples playlists
    devices = query.distinct().all()
    
    # Cargar explícitamente las playlists para cada dispositivo
    for device in devices:
        # SQLAlchemy debería haber cargado las playlists automáticamente,
        # pero podemos forzar la carga si es necesario
        if hasattr(device, 'playlists') and device.playlists is None:
            device_playlists = db.query(models.Playlist).join(
                models.DevicePlaylist,
                models.DevicePlaylist.playlist_id == models.Playlist.id
            ).filter(
                models.DevicePlaylist.device_id == device.device_id
            ).all()
            
            # Asignar manualmente las playlists al dispositivo
            device.playlists = device_playlists
    
    return templates.TemplateResponse(
        "devices.html", 
        {
            "request": request, 
            "title": "Dispositivos Registrados", 
            "devices": devices,
            "active_only": active_only,
            "search_term": search,
            "search_field": search_field
        }
    )

@router.get("/videos", response_class=HTMLResponse)
async def get_videos_page(request: Request):
    """
    Página de gestión de videos y playlists
    """
    # En esta ruta, simplemente renderizamos la plantilla videos.html con los datos básicos
    # Los datos de videos y playlists se cargarán dinámicamente con JavaScript
    return templates.TemplateResponse(
        "videos.html", 
        {
            "request": request, 
            "title": "Gestión de Videos y Listas"
        }
    )

@router.get("/playlists", response_class=HTMLResponse)
async def get_videos_page(request: Request):
    """
    Página de gestión de videos y playlists
    """
    # En esta ruta, simplemente renderizamos la plantilla videos.html con los datos básicos
    # Los datos de videos y playlists se cargarán dinámicamente con JavaScript
    return templates.TemplateResponse(
        "playlists.html", 
        {
            "request": request, 
            "title": "Gestión de Videos y Listas"
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

@router.post("/devices/{device_id}/delete", response_class=HTMLResponse)
async def delete_device_ui(
    request: Request,
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Eliminar un dispositivo
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    db.delete(device)
    db.commit()
    
    # Redirigir a la lista de dispositivos
    return RedirectResponse(url="/ui/devices", status_code=303)

@router.post("/devices/{device_id}/update", response_class=HTMLResponse)
async def update_device_info(
    request: Request,
    device_id: str,
    location: str = Form(None),
    tienda: str = Form(None),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Actualizar información básica de un dispositivo
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Actualizar solo los campos proporcionados
    if location is not None:
        device.location = location
    if tienda is not None:  # Podría ser una cadena vacía
        device.tienda = tienda
    
    device.is_active = is_active
    
    db.commit()
    
    # Redirigir a la página de detalle
    return RedirectResponse(url=f"/ui/devices/{device_id}", status_code=303)