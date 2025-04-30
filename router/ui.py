# Updated router/ui.py with authentication
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import httpx
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Imports from models
from models import models, schemas
from models.database import get_db

# Import authentication utilities
from utils.auth import get_current_active_user

router = APIRouter(
    prefix="/ui",
    tags=["ui"]
)

# Configure templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Main dashboard page
    """
    # Get username from session for template
    username = request.session.get("username", "User")
    is_admin = request.session.get("is_admin", False)
    
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "Raspberry Pi Registry", "username": username, "is_admin": is_admin}
    )

@router.get("/devices", response_class=HTMLResponse)
async def get_devices_page(
    request: Request, 
    active_only: bool = False,
    search: Optional[str] = None,
    search_field: Optional[str] = "all",
    db: Session = Depends(get_db)
):
    """
    Page that shows the list of registered devices
    """
    # Get username from session for template
    username = request.session.get("username", "User")
    is_admin = request.session.get("is_admin", False)
    
    # Base query with join to playlists
    query = db.query(models.Device).outerjoin(
        models.DevicePlaylist,
        models.DevicePlaylist.device_id == models.Device.device_id
    ).outerjoin(
        models.Playlist,
        models.Playlist.id == models.DevicePlaylist.playlist_id
    )
    
    # Additional filters
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
    
    # Use distinct() to avoid duplicates if a device has multiple playlists
    devices = query.distinct().all()
    
    # Explicitly load playlists for each device
    for device in devices:
        # SQLAlchemy should have loaded playlists automatically,
        # but we can force loading if needed
        if hasattr(device, 'playlists') and device.playlists is None:
            device_playlists = db.query(models.Playlist).join(
                models.DevicePlaylist,
                models.DevicePlaylist.playlist_id == models.Playlist.id
            ).filter(
                models.DevicePlaylist.device_id == device.device_id
            ).all()
            
            # Manually assign playlists to the device
            device.playlists = device_playlists
    
    return templates.TemplateResponse(
        "devices.html", 
        {
            "request": request, 
            "title": "Dispositivos Registrados", 
            "devices": devices,
            "active_only": active_only,
            "search_term": search,
            "search_field": search_field,
            "username": username,
            "is_admin": is_admin
        }
    )

@router.get("/videos", response_class=HTMLResponse)
async def get_videos_page(request: Request):
    """
    Videos page
    """
    # Get username from session for template
    username = request.session.get("username", "User")
    is_admin = request.session.get("is_admin", False)
    
    return templates.TemplateResponse(
        "videos.html", 
        {"request": request, "title": "Gestión de Videos", "username": username, "is_admin": is_admin}
    )

@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def get_device_detail(
    request: Request, 
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Device detail page
    """
    # Get username from session for template
    username = request.session.get("username", "User")
    is_admin = request.session.get("is_admin", False)
    
    # Perform query with join to load associated playlists
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Explicitly load the device's playlists
    device_playlists = db.query(models.Playlist).join(
        models.DevicePlaylist,
        models.DevicePlaylist.playlist_id == models.Playlist.id
    ).filter(
        models.DevicePlaylist.device_id == device_id
    ).all()
    
    # Assign playlists to the device
    device.playlists = device_playlists
    
    # Get current date for template comparisons
    now = datetime.now()
    
    # Try to get videoloop service status
    service_status = None
    if device.is_active:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{device.ip_address_lan or device.ip_address_wifi}:8000/service/videoloop/status")
                if response.status_code == 200:
                    service_status = response.json()
        except:
            # If connection fails, set status as unknown
            service_status = {"status": "unknown", "active": False, "enabled": False}
    
    return templates.TemplateResponse(
        "device_detail.html", 
        {
            "request": request, 
            "title": f"Dispositivo: {device.name}",
            "device": device,
            "service_status": service_status,
            "now": now,
            "username": username,
            "is_admin": is_admin
        }
    )

@router.post("/devices/{device_id}/delete", response_class=HTMLResponse)
async def delete_device_ui(
    request: Request,
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a device
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    db.delete(device)
    db.commit()
    
    # Redirect to the devices list
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
    Update basic device information
    """
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Update only provided fields
    if location is not None:
        device.location = location
    if tienda is not None:  # Could be an empty string
        device.tienda = tienda
    
    device.is_active = is_active
    
    db.commit()
    
    # Redirect to the device detail page
    return RedirectResponse(url=f"/ui/devices/{device_id}", status_code=303)

# New route for user administration (only for admins)
@router.get("/users", response_class=HTMLResponse)
async def get_users_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    User administration page (admin only)
    """
    # Check if user is admin
    is_admin = request.session.get("is_admin", False)
    if not is_admin:
        return RedirectResponse(url="/ui/", status_code=303)
        
    # Get username from session for template
    username = request.session.get("username", "User")
    
    # Get all users
    users = db.query(models.User).all()
    
    return templates.TemplateResponse(
        "users.html", 
        {
            "request": request, 
            "title": "Administración de Usuarios",
            "users": users,
            "username": username,
            "is_admin": is_admin
        }
    )