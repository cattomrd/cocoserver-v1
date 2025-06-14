# utils/auth.py - Corrección del middleware de autenticación

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def auth_middleware(public_paths: list = None, admin_paths: list = None):
    """
    Middleware de autenticación mejorado
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
            # Permitir acceso a rutas públicas
            response = await call_next(request)
            return response
        
        # Para rutas protegidas, verificar autenticación
        auth_header = request.headers.get("Authorization")
        
        # Si es una ruta de UI y no hay token, redireccionar a login
        if path.startswith("/ui/") and (not auth_header or not auth_header.startswith("Bearer ")):
            # Construir URL de redirección con next parameter
            next_url = str(request.url)
            login_url = f"/ui/login?next={next_url}"
            return RedirectResponse(url=login_url, status_code=302)
        
        # Para rutas API sin token, devolver 401
        if not auth_header or not auth_header.startswith("Bearer "):
            return HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de acceso requerido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Continuar con la solicitud
        response = await call_next(request)
        return response
    
    return middleware

# Funciones de utilidad para autenticación
def get_current_user_from_request(request: Request):
    """
    Extrae información del usuario desde el request
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    # Aquí deberías decodificar el JWT y obtener la información del usuario
    # Por ahora, retorna None para compatibilidad
    return None

def admin_required(request: Request):
    """
    Dependencia que requiere permisos de administrador
    """
    user = get_current_user_from_request(request)
    if not user or not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos de administrador requeridos"
        )
    return user

# Función de autenticación de usuario (mantener compatibilidad)
async def authenticate_user(db: Session, username: str, password: str):
    """
    Autenticar usuario con username y password
    """
    from models.models import User
    
    user = db.query(User).filter(User.username == username).first()
    if user and user.verify_password(password) and user.is_active:
        user.update_last_login()
        db.commit()
        return user
    return None

# Crear sesión (mantener compatibilidad)
def create_session(user_id: int, username: str, is_admin: bool = False):
    """
    Crear una sesión para el usuario
    """
    # Por ahora, retorna un token simple
    # En producción, usar JWT
    return f"session_{user_id}_{username}"

def get_current_user(request: Request):
    """
    Obtener usuario actual desde el request
    """
    # Implementación básica para mantener compatibilidad
    return get_current_user_from_request(request)