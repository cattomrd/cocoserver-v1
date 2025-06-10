"""
utils/list_checker.py
Verificador de listas de reproducción que se ejecuta en background
para activar/desactivar listas según sus fechas de inicio y fin
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.database import SessionLocal
from models.models import Playlist

# Configurar logging
logger = logging.getLogger(__name__)

class PlaylistChecker:
    """
    Clase para verificar y actualizar el estado de las listas de reproducción
    según sus fechas de inicio y fin
    """
    
    def __init__(self, check_interval: int = 300):  # 5 minutos por defecto
        """
        Inicializar el verificador de listas
        
        Args:
            check_interval: Intervalo en segundos entre verificaciones
        """
        self.check_interval = check_interval
        self.running = False
        
    async def start(self):
        """Iniciar el verificador en background"""
        if self.running:
            logger.warning("El verificador de listas ya está en ejecución")
            return
            
        self.running = True
        logger.info(f"Iniciando verificador de listas cada {self.check_interval} segundos")
        
        try:
            while self.running:
                await self.check_and_update_playlists()
                await asyncio.sleep(self.check_interval)
        except Exception as e:
            logger.error(f"Error en el verificador de listas: {str(e)}")
        finally:
            self.running = False
            
    def stop(self):
        """Detener el verificador"""
        logger.info("Deteniendo verificador de listas")
        self.running = False
        
    async def check_and_update_playlists(self):
        """
        Verificar todas las listas y actualizar su estado según las fechas
        """
        db = SessionLocal()
        try:
            now = datetime.now()
            logger.debug(f"Verificando listas de reproducción - {now}")
            
            # Obtener todas las listas que podrían necesitar actualización
            playlists = db.query(Playlist).filter(
                or_(
                    # Listas que tienen fecha de inicio y podrían necesitar activarse
                    and_(
                        Playlist.start_date.isnot(None),
                        Playlist.start_date <= now,
                        Playlist.is_active == False
                    ),
                    # Listas que tienen fecha de fin y podrían necesitar desactivarse
                    and_(
                        Playlist.expiration_date.isnot(None),
                        Playlist.expiration_date <= now,
                        Playlist.is_active == True
                    ),
                    # Listas que deberían estar activas pero no lo están
                    and_(
                        Playlist.is_active == False,
                        or_(
                            Playlist.start_date.is_(None),
                            Playlist.start_date <= now
                        ),
                        or_(
                            Playlist.expiration_date.is_(None),
                            Playlist.expiration_date > now
                        )
                    )
                )
            ).all()
            
            updated_count = 0
            activated_count = 0
            deactivated_count = 0
            
            for playlist in playlists:
                old_status = playlist.is_active
                new_status = self._should_be_active(playlist, now)
                
                if old_status != new_status:
                    playlist.is_active = new_status
                    updated_count += 1
                    
                    if new_status:
                        activated_count += 1
                        logger.info(f"Lista activada: '{playlist.title}' (ID: {playlist.id})")
                    else:
                        deactivated_count += 1
                        logger.info(f"Lista desactivada: '{playlist.title}' (ID: {playlist.id})")
            
            if updated_count > 0:
                db.commit()
                logger.info(f"Actualización completada: {activated_count} activadas, {deactivated_count} desactivadas")
            else:
                logger.debug("No se requirieron actualizaciones")
                
        except Exception as e:
            logger.error(f"Error al verificar listas: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def _should_be_active(self, playlist: Playlist, now: datetime) -> bool:
        """
        Determinar si una lista debería estar activa según las fechas
        
        Args:
            playlist: La lista de reproducción a verificar
            now: Fecha y hora actual
            
        Returns:
            True si la lista debería estar activa, False en caso contrario
        """
        # Si tiene fecha de inicio y aún no ha llegado, no debe estar activa
        if playlist.start_date and now < playlist.start_date:
            return False
        
        # Si tiene fecha de fin y ya pasó, no debe estar activa
        if playlist.expiration_date and now > playlist.expiration_date:
            return False
        
        # En todos los demás casos, debería estar activa
        return True
    
    def check_playlist_status(self, playlist_id: int, db: Session) -> dict:
        """
        Verificar el estado de una lista específica
        
        Args:
            playlist_id: ID de la lista a verificar
            db: Sesión de base de datos
            
        Returns:
            Diccionario con información del estado de la lista
        """
        playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
        if not playlist:
            return {"error": "Lista no encontrada"}
        
        now = datetime.now()
        should_be_active = self._should_be_active(playlist, now)
        
        status_info = {
            "id": playlist.id,
            "title": playlist.title,
            "current_status": playlist.is_active,
            "should_be_active": should_be_active,
            "needs_update": playlist.is_active != should_be_active,
            "start_date": playlist.start_date.isoformat() if playlist.start_date else None,
            "expiration_date": playlist.expiration_date.isoformat() if playlist.expiration_date else None,
            "checked_at": now.isoformat()
        }
        
        # Información adicional sobre el estado
        if playlist.start_date and now < playlist.start_date:
            time_until_start = playlist.start_date - now
            status_info["status_reason"] = f"Programada para iniciar en {time_until_start}"
        elif playlist.expiration_date and now > playlist.expiration_date:
            time_since_expired = now - playlist.expiration_date
            status_info["status_reason"] = f"Expiró hace {time_since_expired}"
        elif should_be_active:
            status_info["status_reason"] = "Debería estar activa"
        else:
            status_info["status_reason"] = "No cumple criterios de activación"
        
        return status_info

# Instancia global del verificador
playlist_checker = PlaylistChecker()

def start_playlist_checker(app=None, check_interval: int = 300):
    """
    Iniciar el verificador de listas de reproducción
    
    Args:
        app: Instancia de la aplicación FastAPI (opcional)
        check_interval: Intervalo en segundos entre verificaciones
    """
    global playlist_checker
    
    if playlist_checker.running:
        logger.warning("El verificador de listas ya está en ejecución")
        return
    
    playlist_checker = PlaylistChecker(check_interval)
    
    # Si se proporciona una app FastAPI, agregar el evento de inicio
    if app:
        @app.on_event("startup")
        async def startup_event():
            asyncio.create_task(playlist_checker.start())
        
        @app.on_event("shutdown")
        async def shutdown_event():
            playlist_checker.stop()
    else:
        # Iniciar directamente
        asyncio.create_task(playlist_checker.start())
    
    logger.info("Verificador de listas configurado correctamente")

def stop_playlist_checker():
    """Detener el verificador de listas"""
    global playlist_checker
    if playlist_checker:
        playlist_checker.stop()

def get_playlist_status(playlist_id: int) -> dict:
    """
    Obtener el estado actual de una lista específica
    
    Args:
        playlist_id: ID de la lista
        
    Returns:
        Diccionario con información del estado
    """
    db = SessionLocal()
    try:
        return playlist_checker.check_playlist_status(playlist_id, db)
    finally:
        db.close()

# Función para verificación manual
async def manual_check():
    """Ejecutar una verificación manual de todas las listas"""
    global playlist_checker
    if not playlist_checker:
        playlist_checker = PlaylistChecker()
    
    await playlist_checker.check_and_update_playlists()

if __name__ == "__main__":
    # Para pruebas directas
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Ejecutar verificación manual
        asyncio.run(manual_check())
    else:
        # Ejecutar el verificador continuo
        checker = PlaylistChecker(check_interval=60)  # 1 minuto para pruebas
        asyncio.run(checker.start())