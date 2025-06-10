# utils/helpers.py
# Funciones auxiliares actualizadas para manejar fechas de inicio y fin

from datetime import datetime
from typing import Optional
from models.models import Playlist

def is_playlist_active(playlist: Playlist, check_time: Optional[datetime] = None) -> bool:
    """
    Verifica si una playlist está activa considerando las fechas de inicio y fin
    
    Args:
        playlist: La playlist a verificar
        check_time: Momento a verificar (por defecto es ahora)
        
    Returns:
        True si la playlist debería estar activa, False en caso contrario
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Si está marcada como inactiva, no está activa
    if not playlist.is_active:
        return False
    
    # Verificar fecha de inicio
    if playlist.start_date and check_time < playlist.start_date:
        return False
    
    # Verificar fecha de expiración
    if playlist.expiration_date and check_time > playlist.expiration_date:
        return False
    
    return True

def get_playlist_status_info(playlist: Playlist, check_time: Optional[datetime] = None) -> dict:
    """
    Obtiene información detallada del estado de una playlist
    
    Args:
        playlist: La playlist a verificar
        check_time: Momento a verificar (por defecto es ahora)
        
    Returns:
        Diccionario con información del estado
    """
    if check_time is None:
        check_time = datetime.now()
    
    status_info = {
        'id': playlist.id,
        'title': playlist.title,
        'is_active_flag': playlist.is_active,
        'is_currently_active': False,
        'status': 'inactive',
        'reason': '',
        'start_date': playlist.start_date.isoformat() if playlist.start_date else None,
        'expiration_date': playlist.expiration_date.isoformat() if playlist.expiration_date else None,
        'checked_at': check_time.isoformat()
    }
    
    # Si está marcada como inactiva
    if not playlist.is_active:
        status_info['status'] = 'disabled'
        status_info['reason'] = 'Marcada como inactiva'
        return status_info
    
    # Verificar fecha de inicio
    if playlist.start_date and check_time < playlist.start_date:
        time_until_start = playlist.start_date - check_time
        status_info['status'] = 'scheduled'
        status_info['reason'] = f'Programada para iniciar en {format_timedelta(time_until_start)}'
        status_info['time_until_start'] = time_until_start.total_seconds()
        return status_info
    
    # Verificar fecha de expiración
    if playlist.expiration_date and check_time > playlist.expiration_date:
        time_since_expired = check_time - playlist.expiration_date
        status_info['status'] = 'expired'
        status_info['reason'] = f'Expiró hace {format_timedelta(time_since_expired)}'
        status_info['time_since_expired'] = time_since_expired.total_seconds()
        return status_info
    
    # Está activa
    status_info['is_currently_active'] = True
    status_info['status'] = 'active'
    
    # Información adicional sobre cuándo expira
    if playlist.expiration_date:
        time_until_expiration = playlist.expiration_date - check_time
        status_info['reason'] = f'Activa, expira en {format_timedelta(time_until_expiration)}'
        status_info['time_until_expiration'] = time_until_expiration.total_seconds()
    else:
        status_info['reason'] = 'Activa sin fecha de expiración'
    
    return status_info

def format_timedelta(td) -> str:
    """
    Formatea un timedelta en una cadena legible
    
    Args:
        td: timedelta a formatear
        
    Returns:
        Cadena formateada (ej: "2 días, 3 horas")
    """
    if td.total_seconds() < 0:
        return format_timedelta(-td)
    
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} día{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
    if minutes > 0 and days == 0:  # Solo mostrar minutos si no hay días
        parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
    
    if not parts:
        return "menos de 1 minuto"
    
    return ", ".join(parts)

def get_active_playlists_count(playlists: list, check_time: Optional[datetime] = None) -> dict:
    """
    Cuenta las playlists por estado
    
    Args:
        playlists: Lista de playlists a contar
        check_time: Momento a verificar (por defecto es ahora)
        
    Returns:
        Diccionario con conteos por estado
    """
    if check_time is None:
        check_time = datetime.now()
    
    counts = {
        'total': len(playlists),
        'active': 0,
        'scheduled': 0,
        'expired': 0,
        'disabled': 0
    }
    
    for playlist in playlists:
        status_info = get_playlist_status_info(playlist, check_time)
        status = status_info['status']
        
        if status in counts:
            counts[status] += 1
    
    return counts

def should_playlist_be_active(playlist: Playlist, check_time: Optional[datetime] = None) -> bool:
    """
    Determina si una playlist debería estar activa según sus fechas
    (independientemente de su flag is_active actual)
    
    Args:
        playlist: La playlist a verificar
        check_time: Momento a verificar (por defecto es ahora)
        
    Returns:
        True si la playlist debería estar activa según las fechas
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Verificar fecha de inicio
    if playlist.start_date and check_time < playlist.start_date:
        return False
    
    # Verificar fecha de expiración
    if playlist.expiration_date and check_time > playlist.expiration_date:
        return False
    
    return True

def get_next_status_change(playlist: Playlist, check_time: Optional[datetime] = None) -> Optional[dict]:
    """
    Obtiene información sobre el próximo cambio de estado de una playlist
    
    Args:
        playlist: La playlist a verificar
        check_time: Momento a verificar (por defecto es ahora)
        
    Returns:
        Diccionario con información del próximo cambio o None si no hay cambios programados
    """
    if check_time is None:
        check_time = datetime.now()
    
    next_changes = []
    
    # Verificar fecha de inicio
    if playlist.start_date and check_time < playlist.start_date:
        next_changes.append({
            'date': playlist.start_date,
            'type': 'activation',
            'description': 'Se activará'
        })
    
    # Verificar fecha de expiración
    if playlist.expiration_date and check_time < playlist.expiration_date:
        next_changes.append({
            'date': playlist.expiration_date,
            'type': 'expiration',
            'description': 'Expirará'
        })
    
    if not next_changes:
        return None
    
    # Obtener el próximo cambio
    next_change = min(next_changes, key=lambda x: x['date'])
    time_until_change = next_change['date'] - check_time
    
    return {
        'date': next_change['date'].isoformat(),
        'type': next_change['type'],
        'description': next_change['description'],
        'time_until_change': time_until_change.total_seconds(),
        'formatted_time': format_timedelta(time_until_change)
    }

# Función auxiliar para compatibilidad hacia atrás
def manage_service(device_id: str, service_name: str, action: str) -> dict:
    """
    Función auxiliar para gestión de servicios
    (mantener para compatibilidad)
    """
    # Esta función se puede implementar según sea necesario
    # o redirigir a la implementación existente
    return {
        "success": False,
        "message": "Función no implementada en helpers.py"
    }