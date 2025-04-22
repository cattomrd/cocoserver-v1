# Actualización para app/routers/raspberry.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from models.database import get_db
from models.models import Playlist, Video

router = APIRouter(
    prefix="/raspberry",
    tags=["raspberry"]
)

@router.get("/playlists/active")
def get_active_playlists_for_raspberry(
    db: Session = Depends(get_db)
):
    now = datetime.now()
    
    # Obtener todas las playlists activas que no han expirado
    active_playlists = db.query(Playlist).filter(
        Playlist.is_active == True,
        (Playlist.expiration_date == None) | (Playlist.expiration_date > now)
    ).all()
    
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
    playlist_ids: str = None,
    last_update: str = None,
    db: Session = Depends(get_db)
):
    """
    Endpoint para que los clientes Raspberry Pi verifiquen actualizaciones.
    Devuelve playlists modificadas y estado de expiración.
    
    Args:
        playlist_ids: Lista de IDs de playlists separadas por comas (1,2,3)
        last_update: Timestamp ISO de la última actualización
    """
    now = datetime.now()
    updates = {
        "active_playlists": [],
        "expired_playlists": [],
        "timestamp": now.isoformat()
    }
    
    # Si no se proporciona last_update, devolver todas las playlists activas
    if not last_update:
        return get_active_playlists_for_raspberry(db)
    
    # Convertir last_update a datetime
    try:
        last_update_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
    except ValueError:
        last_update_dt = datetime.min
    
    # Si se proporcionaron playlist_ids, verificamos su estado
    if playlist_ids:
        try:
            playlist_id_list = [int(pid) for pid in playlist_ids.split(',')]
            
            # Obtener playlists solicitadas
            for playlist_id in playlist_id_list:
                playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
                
                # Si la playlist no existe o no está activa o ha expirado, agregarla a expired_playlists
                if (not playlist or 
                    not playlist.is_active or 
                    (playlist.expiration_date and playlist.expiration_date < now)):
                    updates["expired_playlists"].append(playlist_id)
            
            # Buscar playlists que se hayan modificado desde last_update
            modified_playlists = db.query(Playlist).filter(
                Playlist.is_active == True,
                (Playlist.expiration_date == None) | (Playlist.expiration_date > now),
                Playlist.id.in_(playlist_id_list)
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
        
        except ValueError:
            pass  # Ignorar si los IDs no son válidos
    
    # Devolver nuevas playlists activas que no estén en la lista proporcionada
    if playlist_id_list:
        new_playlists = db.query(Playlist).filter(
            Playlist.is_active == True,
            (Playlist.expiration_date == None) | (Playlist.expiration_date > now),
            Playlist.id.in_(playlist_id_list)
        ).all()
        
        for playlist in new_playlists:
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