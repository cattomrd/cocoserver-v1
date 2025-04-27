from datetime import datetime
from models.models import Playlist

def is_playlist_active(playlist: Playlist) -> bool:
    """
    Verifica si una playlist está activa basándose en su estado y fecha de expiración
    
    Args:
        playlist (Playlist): Objeto playlist a verificar
        
    Returns:
        bool: True si está activa, False si no
    """
    if not playlist.is_active:
        return False
    if playlist.expiration_date and playlist.expiration_date < datetime.now():
        return False
    return True

async def manage_service(device_id, service_name, action, db):
    """
    Función intermediaria para gestionar servicios.
    Llama a manage_service_via_api.
    """
    from router.device_service_api import manage_service_via_api
    return await manage_service_via_api(device_id, service_name, action, db)