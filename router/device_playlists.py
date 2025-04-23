# Nuevo archivo: router/device_playlists.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models.database import get_db
from models import models, schemas
from utils.helpers import is_playlist_active

router = APIRouter(
    prefix="/api/device-playlists",
    tags=["device-playlists"]
)

@router.post("/", response_model=schemas.DevicePlaylistResponse)
def assign_playlist_to_device(
    assignment: schemas.DevicePlaylistCreate,
    db: Session = Depends(get_db)
):
    """
    Asigna una playlist a un dispositivo.
    Verifica que tanto el dispositivo como la playlist existan.
    """
    # Verificar si el dispositivo existe
    device = db.query(models.Device).filter(models.Device.device_id == assignment.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Verificar si la playlist existe
    playlist = db.query(models.Playlist).filter(models.Playlist.id == assignment.playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist no encontrada")
    
    # Verificar si la asignación ya existe
    existing = db.query(models.DevicePlaylist).filter(
        models.DevicePlaylist.device_id == assignment.device_id,
        models.DevicePlaylist.playlist_id == assignment.playlist_id
    ).first()
    
    if existing:
        return existing  # Si ya existe, simplemente devolver la asignación existente
    
    # Crear nueva asignación
    db_assignment = models.DevicePlaylist(**assignment.dict())
    db.add(db_assignment)
    
    try:
        db.commit()
        db.refresh(db_assignment)
        return db_assignment
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"No se pudo crear la asignación: {str(e)}")

@router.delete("/{device_id}/{playlist_id}")
def remove_playlist_from_device(
    device_id: str,
    playlist_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina la asignación de una playlist a un dispositivo.
    """
    # Buscar la asignación
    assignment = db.query(models.DevicePlaylist).filter(
        models.DevicePlaylist.device_id == device_id,
        models.DevicePlaylist.playlist_id == playlist_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=404, 
            detail="No se encontró la asignación entre el dispositivo y la playlist"
        )
    
    # Eliminar la asignación
    db.delete(assignment)
    db.commit()
    
    return {"message": "Asignación eliminada correctamente"}

@router.get("/device/{device_id}/playlists", response_model=List[schemas.PlaylistInfo])
def get_device_playlists(
    device_id: str, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Obtiene todas las playlists asignadas a un dispositivo específico.
    Puede filtrar para mostrar solo playlists activas.
    """
    # Verificar si el dispositivo existe
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Obtener playlists asignadas al dispositivo
    query = db.query(models.Playlist).join(
        models.DevicePlaylist,
        models.DevicePlaylist.playlist_id == models.Playlist.id
    ).filter(models.DevicePlaylist.device_id == device_id)
    
    # Filtrar por activas si se solicita
    if active_only:
        query = query.filter(models.Playlist.is_active == True)
    
    playlists = query.all()
    
    # Filtrar playlists expiradas si active_only es True
    if active_only:
        from datetime import datetime
        now = datetime.now()
        playlists = [
            p for p in playlists if not p.expiration_date or p.expiration_date > now
        ]
    
    return playlists

@router.get("/playlist/{playlist_id}/devices", response_model=List[schemas.DeviceInfo])
def get_playlist_devices(
    playlist_id: int, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los dispositivos a los que está asignada una playlist específica.
    Puede filtrar para mostrar solo dispositivos activos.
    """
    # Verificar si la playlist existe
    playlist = db.query(models.Playlist).filter(models.Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist no encontrada")
    
    # Obtener dispositivos asignados a la playlist
    query = db.query(models.Device).join(
        models.DevicePlaylist,
        models.DevicePlaylist.device_id == models.Device.device_id
    ).filter(models.DevicePlaylist.playlist_id == playlist_id)
    
    # Filtrar por activos si se solicita
    if active_only:
        query = query.filter(models.Device.is_active == True)
    
    devices = query.all()
    
    return devices