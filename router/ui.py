# Archivo app/routers/ui.py
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import sys
import os

# Añadir la ruta del directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importaciones absolutas en lugar de relativas
from models.models import Device
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
    return templates.TemplateResponse("index.html", {"request": request, "title": "Raspberry Pi Registry"})

@router.get("/devices", response_class=HTMLResponse)
async def get_devices_page(
    request: Request, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Página que muestra la lista de dispositivos registrados
    """
    query = db.query(Device)
    if active_only:
        query = query.filter(Device.is_active == True)
    
    devices = query.all()
    return templates.TemplateResponse(
        "devices.html", 
        {
            "request": request, 
            "title": "Dispositivos Registrados", 
            "devices": devices,
            "active_only": active_only
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
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Intentar obtener el estado del servicio videoloop
    service_status = None
    if device.is_active:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{device.ip_address}:8000/service/videoloop/status")
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
            "service_status": service_status
        }
    )

@router.post("/devices/{device_id}/service", response_class=HTMLResponse)
async def control_device_service(
    request: Request,
    device_id: str,
    action: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Realizar una acción sobre el servicio videoloop (iniciar, detener, reiniciar)
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    result = {"success": False, "message": "No se pudo conectar con el dispositivo"}
    
    # Validar acción
    if action not in ["start", "stop", "restart", "status"]:
        result = {"success": False, "message": f"Acción no válida: {action}"}
    else:
        # Intentar realizar la acción en el dispositivo remoto
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"http://{device.ip_address_lan}:8000/service/videoloop/{action}"
                )
                if response.status_code == 200:
                    result = response.json()
                    # Actualizar el estado del servicio en la base de datos
                    if "status" in result:
                        device.videoloop_status = result["status"]
                        db.commit()
                else:
                    result = {"success": False, "message": f"Error: {response.text}"}
        except Exception as e:
            result = {"success": False, "message": f"Error de conexión: {str(e)}"}
    
    # Redirigir a la página de detalle con un mensaje
    return templates.TemplateResponse(
        "service_control.html", 
        {
            "request": request,
            "title": f"Control de Servicio: {device.name}",
            "device": device,
            "action": action,
            "result": result
        }
    )

# @router.post("/devices/{device_id}/update", response_class=HTMLResponse)
# async def update_device_info(
#     request: Request,
#     device_id: str,
#     name: str = Form(None),
#     location: str = Form(None),
#     is_active: bool = Form(False),
#     db: Session = Depends(get_db)
# ):
#     """
#     Actualizar información básica de un dispositivo
#     """
#     device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
#     if device is None:
#         raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
#     # Actualizar solo los campos proporcionados
#     if name:
#         device.name = name
#     if location is not None:  # Podría ser una cadena vacía
#         device.location = location
    
#     device.is_active = is_active
    
#     db.commit()
    
#     # Redirigir a la página de detalle
#     return RedirectResponse(url=f"/ui/devices/{device_id}", status_code=303)

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

    
    # Redirigir a la página de detalle con un mensaje
    return templates.TemplateResponse(
        "service_control.html", 
        {
            "request": request,
            "title": f"Control de Servicio: {device.name}",
            "device": device,
            "action": action,
            "result": result
        }
    )

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

# @router.post("/devices/{device_id}/delete", response_class=HTMLResponse)
# async def delete_device_ui(
#     request: Request,
#     device_id: str,
#     db: Session = Depends(get_db)
# ):
#     """
#     Eliminar un dispositivo
#     """
#     device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
#     if device is None:
#         raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
#     db.delete(device)
#     db.commit()
    
#     # Redirigir a la lista de dispositivos
#     return RedirectResponse(url="/ui/devices", status_code=303)

