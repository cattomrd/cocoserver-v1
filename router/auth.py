# app/router/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from models.database import get_db
from models import models, schemas
from utils.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user, 
    get_current_active_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

@router.post("/login", response_model=schemas.TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Permite a los usuarios iniciar sesión y obtener un token JWT
    """
    # Autenticar usuario
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear datos para el token
    token_data = {"sub": str(user.id)}
    
    # Generar token de acceso
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Convertir el usuario a esquema de respuesta
    user_response = schemas.UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login
    )
    
    # Retornar el token de acceso
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # en segundos
        "user": user_response
    }

@router.post("/token", response_model=schemas.TokenResponse)
async def get_token(
    login_data: schemas.TokenRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint alternativo para obtener token usando JSON en lugar de form-data
    """
    # Autenticar usuario
    user = authenticate_user(login_data.username, login_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos"
        )
    
    # Crear datos para el token
    token_data = {"sub": str(user.id)}
    
    # Generar token de acceso
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Convertir el usuario a esquema de respuesta
    user_response = schemas.UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login
    )
    
    # Retornar el token de acceso
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # en segundos
        "user": user_response
    }

@router.post("/register", response_model=schemas.UserResponse)
async def register_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Permite a los usuarios registrarse en el sistema
    """
    # Verificar si el nombre de usuario ya existe
    db_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado"
        )
    
    # Verificar si el correo electrónico ya existe
    db_email = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Crear nuevo usuario
    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        is_active=True,
        is_admin=False,  # Los usuarios registrados no son administradores por defecto
        created_at=datetime.now()
    )
    # Establecer la contraseña (será hasheada por el setter)
    new_user.password = user_data.password
    
    # Guardar en la base de datos
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return schemas.UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        is_admin=new_user.is_admin,
        created_at=new_user.created_at,
        last_login=new_user.last_login
    )

@router.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(
    current_user: models.User = Depends(get_current_user)
):
    """
    Devuelve la información del usuario actualmente autenticado
    """
    return current_user

@router.put("/users/me", response_model=schemas.UserResponse)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite al usuario actualizar su propia información
    """
    # No permitir cambiar is_admin desde aquí
    if hasattr(user_update, 'is_admin'):
        delattr(user_update, 'is_admin')
    
    # Actualizar los campos proporcionados
    update_data = user_update.dict(exclude_unset=True, exclude={'is_admin'})
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/users/me/change-password", response_model=dict)
async def change_password(
    password_data: schemas.PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite al usuario cambiar su contraseña
    """
    # Verificar la contraseña actual
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )
    
    # Cambiar la contraseña
    current_user.password = password_data.new_password
    db.commit()
    
    return {"message": "Contraseña actualizada correctamente"}

# === Endpoints de administración de usuarios (solo para administradores) ===

@router.get("/users", response_model=List[schemas.UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de usuarios (solo administradores)
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: int,
    current_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Obtiene un usuario por su ID (solo administradores)
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return user

@router.put("/users/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Actualiza un usuario por su ID (solo administradores)
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Actualizar los campos proporcionados
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """
    Elimina un usuario por su ID (solo administradores)
    """
    # No permitir eliminar al propio usuario administrador
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta de administrador"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "Usuario eliminado correctamente"}