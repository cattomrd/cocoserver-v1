# app/utils/auth.py

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import ValidationError
from   fastapi import Request

from models.database import get_db
from models import models, schemas

# Configuración de JWT
# Estos valores deberían idealmente estar en variables de entorno
SECRET_KEY = "b1fc0d5b9b3a41ae5c16d3a3e5ba609b60f13e3f92ce336a2c50d43ec24ae612"  # Cambiar por tu clave secreta
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

# Configurar OAuth2 para obtener token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Genera un nuevo token JWT con los datos proporcionados"""
    to_encode = data.copy()
    
    # Establecer expiración del token
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Codificar token JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verifica y decodifica un token JWT"""
    try:
        # Decodificar el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extraer datos del payload
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        
        token_data = {"user_id": user_id}
        return token_data
    except JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependencia para obtener el usuario actual a partir del token JWT.
    Se utiliza para proteger rutas que requieren autenticación.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verificar token
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    # Obtener usuario de la base de datos
    user = db.query(models.User).filter(models.User.id == token_data["user_id"]).first()
    if user is None:
        raise credentials_exception
    
    # Verificar que el usuario esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    return user

async def get_current_active_admin(current_user: models.User = Depends(get_current_user)):
    """
    Dependencia para obtener el usuario administrador actual.
    Se utiliza para proteger rutas que requieren permisos de administrador.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene permisos suficientes"
        )
    return current_user

def authenticate_user(username: str, password: str, db: Session):
    """
    Autentica un usuario verificando su nombre de usuario y contraseña.
    
    Args:
        username: Nombre de usuario o correo electrónico
        password: Contraseña en texto plano
        db: Sesión de la base de datos
    
    Returns:
        El usuario si la autenticación es exitosa, None en caso contrario
    """
    # Buscar usuario por nombre de usuario o correo electrónico
    user = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == username)
    ).first()
    
    # Verificar si el usuario existe y la contraseña es correcta
    if not user or not user.verify_password(password):
        return None
    
    # Actualizar la fecha del último inicio de sesión
    user.last_login = datetime.now()
    db.commit()
    
    return user

def get_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    """
    Función auxiliar para obtener el usuario a partir de la cookie de sesión.
    No modifica el sistema OAuth2 existente.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )
    
    # Obtener token de la cookie
    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception
    
    # Verificar el token
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    # Obtener usuario de la base de datos
    user = db.query(models.User).filter(models.User.id == token_data["user_id"]).first()
    if user is None or not user.is_active:
        raise credentials_exception
        
    return user