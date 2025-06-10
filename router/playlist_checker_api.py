# router/playlist_checker_api.py
# API endpoints para el verificador de listas de reproducción

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from models.database import get_db
from models.models import Playlist
from utils.list_checker import playlist_checker, get_playlist_status, manual_check
from utils.auth import admin_required

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/playlist-checker",
    tags=["playlist-checker"]
)

@router.get("/status")
async def get_checker_status():
    """
    Obtener el estado actual del verificador de listas
    """
    return {
        "running": playlist_checker.running if playlist_checker else False,
        "check_interval": playlist_checker.check_interval if playlist_checker else None,
        "last_check": "No disponible"  # Se puede agregar timestamp del último check
    }

@router.post("/manual-check")
async def trigger_manual_check(admin_user = Depends(admin_required)):
    """
    Ejecutar una verificación manual de todas las listas
    Solo accesible por administradores
    """
    try:
        await manual_check()
        logger.info(f"Verificación manual ejecutada por {admin_user['username']}")
        return {
            "success": True,
            "message": "Verificación manual completada",
            "executed_by": admin_user['username']
        }
    except Exception as e:
        logger.error(f"Error en verificación manual: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al ejecutar verificación: {str(e)}")

@router.get("/playlist/{playlist_id}/status")
async def get_single_playlist_status(playlist_id: int, db: Session = Depends(get_db)):
    """
    Obtener el estado detallado de una lista específica
    """
    try:
        status_info = get_playlist_status(playlist_id)
        
        if "error" in status_info:
            raise HTTPException(status_code=404, detail=status_info["error"])
        
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener estado de playlist {playlist_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/all-playlists/status")
async def get_all_playlists_status(db: Session = Depends(get_db)):
    """
    Obtener el estado de todas las listas de reproducción
    """
    try:
        playlists = db.query(Playlist).all()
        
        results = []
        for playlist in playlists:
            try:
                status_info = playlist_checker.check_playlist_status(playlist.id, db)
                results.append(status_info)
            except Exception as e:
                logger.error(f"Error al verificar playlist {playlist.id}: {str(e)}")
                results.append({
                    "id": playlist.id,
                    "title": playlist.title,
                    "error": str(e)
                })
        
        # Estadísticas resumidas
        active_count = sum(1 for r in results if r.get("should_be_active", False))
        needs_update_count = sum(1 for r in results if r.get("needs_update", False))
        
        return {
            "playlists": results,
            "summary": {
                "total": len(results),
                "should_be_active": active_count,
                "should_be_inactive": len(results) - active_count,
                "needs_update": needs_update_count
            }
        }
    except Exception as e:
        logger.error(f"Error al obtener estado de todas las playlists: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/playlist/{playlist_id}/force-update")
async def force_playlist_update(
    playlist_id: int, 
    db: Session = Depends(get_db),
    admin_user = Depends(admin_required)
):
    """
    Forzar la actualización del estado de una lista específica
    Solo accesible por administradores
    """
    try:
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Lista no encontrada")
        
        # Verificar el estado actual y el que debería tener
        status_info = playlist_checker.check_playlist_status(playlist_id, db)
        
        if not status_info.get("needs_update", False):
            return {
                "success": True,
                "message": "La lista ya tiene el estado correcto",
                "current_status": status_info["current_status"],
                "should_be_active": status_info["should_be_active"]
            }
        
        # Actualizar el estado
        from datetime import datetime
        now = datetime.now()
        new_status = playlist_checker._should_be_active(playlist, now)
        
        old_status = playlist.is_active
        playlist.is_active = new_status
        db.commit()
        
        logger.info(f"Estado de playlist {playlist_id} actualizado por {admin_user['username']}: {old_status} -> {new_status}")
        
        return {
            "success": True,
            "message": f"Estado actualizado: {'activada' if new_status else 'desactivada'}",
            "old_status": old_status,
            "new_status": new_status,
            "updated_by": admin_user['username']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al forzar actualización de playlist {playlist_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar: {str(e)}")

@router.get("/upcoming-activations")
async def get_upcoming_activations(hours: int = 24, db: Session = Depends(get_db)):
    """
    Obtener listas que se activarán en las próximas X horas
    """
    try:
        from datetime import datetime, timedelta
        
        now = datetime.now()
        future_time = now + timedelta(hours=hours)
        
        # Buscar listas que se activarán en el período especificado
        upcoming_playlists = db.query(Playlist).filter(
            Playlist.start_date.isnot(None),
            Playlist.start_date > now,
            Playlist.start_date <= future_time,
            Playlist.is_active == False
        ).all()
        
        results = []
        for playlist in upcoming_playlists:
            time_until_activation = playlist.start_date - now
            results.append({
                "id": playlist.id,
                "title": playlist.title,
                "start_date": playlist.start_date.isoformat(),
                "time_until_activation": str(time_until_activation),
                "hours_until_activation": time_until_activation.total_seconds() / 3600
            })
        
        return {
            "upcoming_activations": results,
            "count": len(results),
            "period_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Error al obtener activaciones próximas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/expiring-soon")
async def get_expiring_playlists(hours: int = 24, db: Session = Depends(get_db)):
    """
    Obtener listas que expirarán en las próximas X horas
    """
    try:
        from datetime import datetime, timedelta
        
        now = datetime.now()
        future_time = now + timedelta(hours=hours)
        
        # Buscar listas que expirarán en el período especificado
        expiring_playlists = db.query(Playlist).filter(
            Playlist.expiration_date.isnot(None),
            Playlist.expiration_date > now,
            Playlist.expiration_date <= future_time,
            Playlist.is_active == True
        ).all()
        
        results = []
        for playlist in expiring_playlists:
            time_until_expiration = playlist.expiration_date - now
            results.append({
                "id": playlist.id,
                "title": playlist.title,
                "expiration_date": playlist.expiration_date.isoformat(),
                "time_until_expiration": str(time_until_expiration),
                "hours_until_expiration": time_until_expiration.total_seconds() / 3600
            })
        
        return {
            "expiring_soon": results,
            "count": len(results),
            "period_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Error al obtener expiraciones próximas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")