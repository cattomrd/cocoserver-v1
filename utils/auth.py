# app/utils/auth.py

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import ValidationError
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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

async def get_token_from_request(request: Request):
    # Intenta obtener el token de la cookie primero
    token = request.cookies.get("access_token")  # Ajusta el nombre de la cookie según tu configuración
    
    # Si no hay token en la cookie, intenta obtenerlo del header de autorización
    if not token:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token

# Modifica la función get_current_user para usar la nueva dependencia
async def get_current_user(token: str = Depends(get_token_from_request), db: Session = Depends(get_db)):
    # El resto de la función permanece igual
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verificar token
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception

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


    return user