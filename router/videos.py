#Corrección para router/videos.py

import os
import shutil
import uuid
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Body, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.database import get_db
from models.models import Video
from models.schemas import  VideoResponse, VideoUpdate

# Configurar logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/videos",
    tags=["videos"]
)

# Directorio para almacenar videos
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=VideoResponse)
async def create_video(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    expiration_date: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Validar que el archivo sea un video
        if not file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="El archivo debe ser un video")
        
        # Crear un nombre único para el archivo
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Guardar el archivo
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Obtener el tamaño del archivo
        file_size = os.path.getsize(file_path)
        
        # Convertir la fecha de expiración si se proporcionó
        expiration_date_obj = None
        if expiration_date:
            try:
                expiration_date_obj = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha de expiración inválido")
        
        # Crear el objeto de video
        db_video = Video(
            title=title,
            description=description,
            file_path=file_path,
            file_size=file_size,  # Asegurar que se guarda el tamaño
            duration=None,  # TODO: implementar obtención de duración
            expiration_date=expiration_date_obj
        )
        
        # Guardar en la base de datos
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        
        return db_video

    except HTTPException:
        # Re-lanzar excepciones HTTP para preservar códigos de estado
        raise
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except Exception as e:
        logger.error(f"Error al crear video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al crear video: {str(e)}")

@router.get("/", response_model=List[VideoResponse])
def read_videos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Video)
        
        # Si se solicitan solo videos activos, filtrar por fecha de expiración
        if active_only:
            now = datetime.now()
            query = query.filter(
                (Video.expiration_date == None) | (Video.expiration_date > now)
            )
        
        videos = query.offset(skip).limit(limit).all()
        
        # Logging para diagnóstico
        logger.info(f"Recuperados {len(videos)} videos de la base de datos")
        
        # Validar que tengamos datos correctos antes de devolverlos
        for video in videos:
            if not hasattr(video, 'id') or not video.id:
                logger.error(f"Video con ID inválido: {video}")
                raise ValueError("Video con ID inválido encontrado en la base de datos")
        
        return videos
    
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos al leer videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except Exception as e:
        logger.error(f"Error al leer videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener videos: {str(e)}")

@router.get("/{video_id}", response_model=VideoResponse)
def read_video(
    video_id: int, 
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video is None:
            raise HTTPException(status_code=404, detail="Video no encontrado")
        return video
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al obtener video: {str(e)}")

@router.put("/{video_id}", response_model=VideoResponse)
def update_video(
    video_id: int,
    video_update: VideoUpdate,
    db: Session = Depends(get_db)
):
    try:
        db_video = db.query(Video).filter(Video.id == video_id).first()
        if db_video is None:
            raise HTTPException(status_code=404, detail="Video no encontrado")
        
        # Actualizar solo los campos proporcionados
        update_data = video_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_video, key, value)
        
        db.commit()
        db.refresh(db_video)
        return db_video
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al actualizar video: {str(e)}")

@router.get("/{video_id}/download")
def download_video(
    video_id: int, 
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video is None:
            raise HTTPException(status_code=404, detail="Video no encontrado")
        
        # Verificar si el video ha expirado
        if video.expiration_date and video.expiration_date < datetime.now():
            raise HTTPException(status_code=403, detail="Este video ha expirado y ya no está disponible")
        
        file_path = video.file_path
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Archivo de video no encontrado")
        
        return FileResponse(
            path=file_path, 
            filename=os.path.basename(file_path), 
            media_type="video/mp4"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al descargar video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al descargar video: {str(e)}")

@router.delete("/{video_id}")
def delete_video(
    video_id: int, 
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video is None:
            raise HTTPException(status_code=404, detail="Video no encontrado")
        
        # Eliminar el archivo físico
        if os.path.exists(video.file_path):
            os.remove(video.file_path)
        
        # Eliminar de la base de datos
        db.delete(video)
        db.commit()
        
        return {"message": "Video eliminado correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar video: {str(e)}")