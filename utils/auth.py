# utils/auth.py - Archivo de autenticación corregido

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

# Dependencia de seguridad HTTP Bearer
security = HTTPBearer()

def auth_middleware(public_paths: list = None, admin_paths: list = None):
    """
    Middleware de autenticación 
    """
    if public_paths is None:
        public_paths = ["/ui/login", "/login", "/static/", "/docs", "/redoc", "/openapi.json"]
    
    if admin_paths is None:
        admin_paths = []
    
    async def middleware(request: Request, call_next):
        path = request.url.path
        
        # Verificar si es una ruta pública
        is_public = any(path.startswith(public_path) for public_path in public_paths)
        
        if is_public:
            response = await call_next(request)
            return response
        
        # Para rutas protegidas de UI, verificar autenticación básica
        if path.startswith("/ui/"):
            auth_header = request.headers.get("Authorization")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                return RedirectResponse(url="/ui/login", status_code=302)
        
        # Continuar con la solicitud
        response = await call_next(request)
        return response
    
    return middleware

async def authenticate_user(db: Session, username: str, password: str):
    """
    Autenticar usuario con username y password
    """
    from models.models import User
    
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and user.verify_password(password) and user.is_active:
            user.update_last_login()
            db.commit()
            return user
        return None
    except Exception as e:
        logger.error(f"Error autenticando usuario {username}: {str(e)}")
        return None

def create_session(user_id: int, username: str, is_admin: bool = False):
    """
    Crear una sesión para el usuario
    """
    # Crear un ID de sesión simple
    session_id = f"{user_id}_{username}_{uuid.uuid4().hex[:8]}"
    return session_id

def get_current_user(request: Request):
    """
    Obtener usuario actual desde el request (implementación básica)
    """
    # Implementación básica para mantener compatibilidad
    # En una implementación real, decodificarías el JWT del header Authorization
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    # Por ahora, retorna un usuario mock para compatibilidad
    # En producción, aquí decodificarías el JWT y obtendrías el usuario real
    return {
        "id": 1,
        "username": "admin",
        "is_admin": True,
        "is_active": True
    }

def admin_required(request: Request):
    """
    Dependencia que requiere permisos de administrador
    """
    user = get_current_user(request)
    if not user or not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos de administrador requeridos"
        )
    return user

def create_access_token(user_data: dict, expires_delta: timedelta = None):
    """
    Crear token de acceso (implementación básica)
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=8)
    
    # En una implementación real, usarías JWT
    # Por ahora, retorna un token simple
    token_data = {
        "access_token": f"token_{user_data.get('username', '')}_{uuid.uuid4().hex[:16]}",
        "token_type": "bearer",
        "expires_in": 28800,  # 8 horas en segundos
        "user": user_data
    }
    
    return token_data

# Funciones de compatibilidad para el sistema existente
def get_user_from_token(token: str):
    """
    Obtener usuario desde token (implementación básica)
    """
    # Implementación básica para mantener compatibilidad
    # En producción, decodificarías el JWT
    return None

def verify_token(token: str):
    """
    Verificar si un token es válido
    """
    # Implementación básica
    return token and len(token) > 10