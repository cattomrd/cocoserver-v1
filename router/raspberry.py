# Actualización para router/raspberry.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from models.database import get_db
from models.models import Playlist, Video, Device, DevicePlaylist

router = APIRouter(
    prefix="/raspberry",
    tags=["raspberry"]
)

@router.get("/playlists/active")
def get_active_playlists_for_raspberry(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Devuelve todas las playlists activas.
    Si se proporciona un device_id, devuelve solo las playlists asignadas a ese dispositivo.
    """
    now = datetime.now()
    
    # Construir la consulta base para playlists activas
    query = db.query(Playlist).filter(
        Playlist.is_active == True,
        (Playlist.expiration_date == None) | (Playlist.expiration_date > now)
    )
    
    # Si se proporciona un device_id, filtrar por playlists asignadas a ese dispositivo
    if device_id:
        # Verificar que el dispositivo existe
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        
        # Filtrar playlists asignadas al dispositivo
        query = query.join(
            DevicePlaylist,
            DevicePlaylist.playlist_id == Playlist.id
        ).filter(DevicePlaylist.device_id == device_id)
    
    # Ejecutar la consulta
    active_playlists = query.all()
    
    result = []
    for playlist in active_playlists:
        # Filtrar videos que no han expirado
        active_videos = [
            video for video in playlist.videos 
            if not video.expiration_date or video.expiration_date > now
        ]
        
        # Solo incluir playlists que tengan al menos un video activo
        if active_videos:
            playlist_data = {
                "id": playlist.id,
                "title": playlist.title,
                "description": playlist.description,
                "expiration_date": playlist.expiration_date.isoformat() if playlist.expiration_date else None,
                "videos": [
                    {
                        "id": video.id,
                        "title": video.title,
                        "file_path": f"/api/videos/{video.id}/download",
                        "duration": video.duration,
                        "expiration_date": video.expiration_date.isoformat() if video.expiration_date else None
                    }
                    for video in active_videos
                ]
            }
            result.append(playlist_data)
    
    return result

@router.get("/check-updates")
def check_for_updates(
    device_id: Optional[str] = None,
    playlist_ids: str = None,
    last_update: str = None,
    db: Session = Depends(get_db)
):
    """
    Endpoint para que los clientes Raspberry Pi verifiquen actualizaciones.
    Devuelve playlists modificadas y estado de expiración.
    
    Args:
        device_id: ID del dispositivo que solicita actualizaciones
        playlist_ids: Lista de IDs de playlists separadas por comas (1,2,3)
        last_update: Timestamp ISO de la última actualización
    """
    now = datetime.now()
    updates = {
        "active_playlists": [],
        "expired_playlists": [],
        "timestamp": now.isoformat()
    }
    
    # Si no se proporciona last_update o device_id, devolver todas las playlists activas
    if not last_update or not device_id:
        return get_active_playlists_for_raspberry(device_id, db)
    
    # Convertir last_update a datetime
    try:
        last_update_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
    except ValueError:
        last_update_dt = datetime.min
    
    # Verificar si el dispositivo existe
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    
    # Si se proporcionaron playlist_ids específicos, verificamos su estado
    if playlist_ids:
        try:
            playlist_id_list = [int(pid) for pid in playlist_ids.split(',')]
            
            # Obtener playlists solicitadas
            for playlist_id in playlist_id_list:
                # Verificar si la playlist existe y está asignada al dispositivo
                playlist = db.query(Playlist).join(
                    DevicePlaylist,
                    DevicePlaylist.playlist_id == Playlist.id
                ).filter(
                    Playlist.id == playlist_id,
                    DevicePlaylist.device_id == device_id
                ).first()
                
                # Si la playlist no existe, no está asignada, no está activa o ha expirado
                if (not playlist or 
                    not playlist.is_active or 
                    (playlist.expiration_date and playlist.expiration_date < now)):
                    updates["expired_playlists"].append(playlist_id)
        except ValueError:
            pass  # Ignorar si los IDs no son válidos
    
    # Obtener playlists asignadas al dispositivo que han sido modificadas desde last_update
    modified_playlists = db.query(Playlist).join(
        DevicePlaylist,
        DevicePlaylist.playlist_id == Playlist.id
    ).filter(
        DevicePlaylist.device_id == device_id,
        Playlist.is_active == True,
        (Playlist.expiration_date == None) | (Playlist.expiration_date > now),
        Playlist.updated_at > last_update_dt
    ).all()
    
    # Incluir solo las que tienen videos activos
    for playlist in modified_playlists:
        active_videos = [v for v in playlist.videos 
                        if not v.expiration_date or v.expiration_date > now]
        
        if active_videos:
            updates["active_playlists"].append({
                "id": playlist.id,
                "title": playlist.title,
                "description": playlist.description,
                "expiration_date": playlist.expiration_date.isoformat() if playlist.expiration_date else None,
                "videos": [
                    {
                        "id": v.id,
                        "title": v.title,
                        "file_path": f"/api/videos/{v.id}/download",
                        "duration": v.duration,
                        "expiration_date": v.expiration_date.isoformat() if v.expiration_date else None
                    }
                    for v in active_videos
                ]
            })
    
    # También buscar playlists recién asignadas al dispositivo
    new_assignments = db.query(Playlist).join(
        DevicePlaylist,
        DevicePlaylist.playlist_id == Playlist.id
    ).filter(
        DevicePlaylist.device_id == device_id,
        Playlist.is_active == True,
        (Playlist.expiration_date == None) | (Playlist.expiration_date > now),
        DevicePlaylist.assigned_at > last_update_dt
    ).all()
    
    # Incluir solo las playlists recién asignadas que no estén ya en active_playlists
    existing_ids = {p["id"] for p in updates["active_playlists"]}
    for playlist in new_assignments:
        if playlist.id not in existing_ids:
            active_videos = [v for v in playlist.videos 
                            if not v.expiration_date or v.expiration_date > now]
            
            if active_videos:
                updates["active_playlists"].append({
                    "id": playlist.id,
                    "title": playlist.title,
                    "description": playlist.description,
                    "expiration_date": playlist.expiration_date.isoformat() if playlist.expiration_date else None,
                    "videos": [
                        {
                            "id": v.id,
                            "title": v.title,
                            "file_path": f"/api/videos/{v.id}/download",
                            "duration": v.duration,
                            "expiration_date": v.expiration_date.isoformat() if v.expiration_date else None
                        }
                        for v in active_videos
                    ]
                })
    
    return updates