import os
import uuid
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime

from models.database import get_db
from models.models import Playlist, Video
from models.schemas import PlaylistCreate, PlaylistResponse, PlaylistUpdate
from utils.helpers import is_playlist_active

router = APIRouter(
    prefix="/playlists",
    tags=["playlists"]
)

# Directorio para archivos de playlist
PLAYLIST_DIR = "playlists"

@router.post("/", response_model=PlaylistResponse)
def create_playlist(
    playlist: PlaylistCreate, 
    db: Session = Depends(get_db)
):
    db_playlist = Playlist(**playlist.dict())
    db.add(db_playlist)
    db.commit()
    db.refresh(db_playlist)
    return db_playlist

@router.get("/", response_model=List[PlaylistResponse])
def read_playlists(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Playlist)
    
    if active_only:
        now = datetime.now()
        query = query.filter(
            Playlist.is_active == True,
            (Playlist.expiration_date == None) | (Playlist.expiration_date > now)
        )
    
    playlists = query.offset(skip).limit(limit).all()
    return playlists

@router.get("/{playlist_id}", response_model=PlaylistResponse)
def read_playlist(
    playlist_id: int, 
    db: Session = Depends(get_db)
):
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    return playlist

@router.put("/{playlist_id}", response_model=PlaylistResponse)
def update_playlist(
    playlist_id: int, 
    playlist_update: PlaylistUpdate, 
    db: Session = Depends(get_db)
):
    db_playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    
    # Actualizar solo los campos proporcionados
    update_data = playlist_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_playlist, key, value)
    
    db.commit()
    db.refresh(db_playlist)
    return db_playlist

@router.delete("/{playlist_id}")
def delete_playlist(
    playlist_id: int, 
    db: Session = Depends(get_db)
):
    db_playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    
    db.delete(db_playlist)
    db.commit()
    
    return {"message": "Lista de reproducción eliminada correctamente"}

@router.post("/{playlist_id}/videos/{video_id}")
def add_video_to_playlist(
    playlist_id: int, 
    video_id: int, 
    db: Session = Depends(get_db)
):
    db_playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    
    db_video = db.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    db_playlist.videos.append(db_video)
    db.commit()
    
    return {"message": "Video añadido a la lista de reproducción correctamente"}

@router.delete("/{playlist_id}/videos/{video_id}")
def remove_video_from_playlist(
    playlist_id: int, 
    video_id: int, 
    db: Session = Depends(get_db)
):
    db_playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    
    db_video = db.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    if db_video in db_playlist.videos:
        db_playlist.videos.remove(db_video)
        db.commit()
        return {"message": "Video eliminado de la lista de reproducción correctamente"}
    else:
        raise HTTPException(
            status_code=404, 
            detail="El video no se encuentra en esta lista de reproducción"
        )

@router.get("/{playlist_id}/download")
def download_playlist(
    playlist_id: int, 
    db: Session = Depends(get_db)
):
    db_playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    
    if not is_playlist_active(db_playlist):
        raise HTTPException(
            status_code=403, 
            detail="Esta lista de reproducción no está activa o ha expirado"
        )
    
    # Crear un archivo JSON con la información de la playlist y los videos
    playlist_data = {
        "id": db_playlist.id,
        "title": db_playlist.title,
        "description": db_playlist.description,
        "expiration_date": db_playlist.expiration_date.isoformat() if db_playlist.expiration_date else None,
        "videos": [
            {
                "id": video.id,
                "title": video.title,
                "description": video.description,
                "file_path": video.file_path,
                "duration": video.duration
            }
            for video in db_playlist.videos
        ]
    }
    
    # Crear un archivo JSON temporal
    playlist_filename = f"playlist_{db_playlist.id}_{uuid.uuid4()}.json"
    playlist_file_path = os.path.join(PLAYLIST_DIR, playlist_filename)
    
    with open(playlist_file_path, "w") as f:
        json.dump(playlist_data, f, indent=4)
    
    return FileResponse(
        path=playlist_file_path, 
        filename=f"playlist_{db_playlist.title.replace(' ', '_')}.json", 
        media_type="application/json"
    )

@router.post("/{playlist_id}/videos/{video_id}")
def add_video_to_playlist(playlist_id: int, video_id: int, db: Session = Depends(get_db)):
    """
    Añade un video a una playlist.
    Verifica si el video ya está en la playlist para evitar duplicados.
    """
    db_playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    
    db_video = db.query(Video).filter(Video.id == video_id).first()
    if db_video is None:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    # Verificar si el video ya está en la playlist
    if db_video in db_playlist.videos:
        # Si ya está, simplemente retornar un mensaje de éxito sin intentar añadirlo de nuevo
        return {"message": "El video ya está en la lista de reproducción"}
    
    # Si no está, añadirlo
    db_playlist.videos.append(db_video)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al añadir el video: {str(e)}")
    
    return {"message": "Video añadido a la lista de reproducción correctamente"}

@router.get("playlists/active") 
def get_active_videos_in_playlist(
    playlist_id: int, 
    db: Session = Depends(get_db)
):
    """
    Devuelve los videos activos en una playlist.
    """
    db_playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if db_playlist is None:
        raise HTTPException(status_code=404, detail="Lista de reproducción no encontrada")
    
    now = datetime.now()
    active_videos = [
        video for video in db_playlist.videos 
        if not video.expiration_date or video.expiration_date > now
    ]
    
    return active_videos
#     return {"active_videos": active_videos}
#     return {"active_videos": [video.id for video in active_videos]}
#     return {"active_videos": [video.title for video in active_videos]}           