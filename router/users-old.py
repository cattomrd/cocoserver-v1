# router/users.py
from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
from sqlalchemy.orm import Session
from typing import List, Optional

from models.database import get_db
from models.models import User
from models.schemas import UserCreate, UserUpdate, UserResponse
from utils.auth import admin_required, get_current_user

# Setup logging
logger = logging.getLogger(__name__)

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/ui/users",
    tags=["user management"]
)

# API routes for user management
@router.get("/", response_class=HTMLResponse)
async def list_users_page(
    request: Request,
    db: Session = Depends(get_db),
    admin_user = Depends(admin_required),
    search: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    Page for listing and managing users
    Only accessible by admin users
    """
    # Build the query
    query = db.query(User)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) |
            (User.fullname.ilike(search_term))
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
        
    # Execute the query
    users = query.all()
    
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "title": "Gestión de Usuarios",
            "users": users,
            "search": search,
            "is_active": is_active,
            "current_user": admin_user
        }
    )

@router.get("/create", response_class=HTMLResponse)
async def create_user_page(
    request: Request,
    admin_user = Depends(admin_required)
):
    """
    Page for creating a new user
    Only accessible by admin users
    """
    return templates.TemplateResponse(
        "user_create.html",
        {
            "request": request,
            "title": "Crear Nuevo Usuario",
            "current_user": admin_user
        }
    )

@router.post("/create", response_class=HTMLResponse)
async def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    fullname: Optional[str] = Form(None),
    is_admin: bool = Form(False),
    is_active: bool = Form(True),
    db: Session = Depends(get_db),
    admin_user = Depends(admin_required)
):
    """
    Handle form submission for creating a new user
    Only accessible by admin users
    """
    # Simple validation
    if password != password_confirm:
        return templates.TemplateResponse(
            "user_create.html",
            {
                "request": request,
                "title": "Crear Nuevo Usuario",
                "error": "Las contraseñas no coinciden",
                "username": username,
                "email": email,
                "fullname": fullname,
                "is_admin": is_admin,
                "is_active": is_active,
                "current_user": admin_user
            }
        )
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse(
            "user_create.html",
            {
                "request": request,
                "title": "Crear Nuevo Usuario",
                "error": "El nombre de usuario ya existe",
                "username": username,
                "email": email,
                "fullname": fullname,
                "is_admin": is_admin,
                "is_active": is_active,
                "current_user": admin_user
            }
        )
        
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        return templates.TemplateResponse(
            "user_create.html",
            {
                "request": request,
                "title": "Crear Nuevo Usuario",
                "error": "El correo electrónico ya está registrado",
                "username": username,
                "email": email,
                "fullname": fullname,
                "is_admin": is_admin,
                "is_active": is_active,
                "current_user": admin_user
            }
        )
    
    # Create the user
    try:
        user = User.create_user(
            db=db,
            username=username,
            email=email,
            password=password,
            fullname=fullname,
            is_admin=is_admin
        )
        user.is_active = is_active
        db.commit()
        
        logger.info(f"Usuario {username} creado por {admin_user['username']}")
        
        # Redirect to user list with success message
        return RedirectResponse(
            url="/ui/users/?success=Usuario creado correctamente", 
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        logger.error(f"Error al crear usuario: {str(e)}")
        return templates.TemplateResponse(
            "user_create.html",
            {
                "request": request,
                "title": "Crear Nuevo Usuario",
                "error": f"Error al crear usuario: {str(e)}",
                "username": username,
                "email": email,
                "fullname": fullname,
                "is_admin": is_admin,
                "is_active": is_active,
                "current_user": admin_user
            }
        )

@router.get("/{user_id}", response_class=HTMLResponse)
async def user_detail_page(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin_user = Depends(admin_required)
):
    """
    Page for viewing and editing a user
    Only accessible by admin users
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "title": f"Usuario: {user.username}",
            "user": user,
            "current_user": admin_user
        }
    )

@router.post("/{user_id}/update", response_class=HTMLResponse)
async def update_user(
    request: Request,
    user_id: int,
    email: str = Form(...),
    fullname: Optional[str] = Form(None),
    is_admin: bool = Form(False),
    is_active: bool = Form(True),
    password: Optional[str] = Form(None),
    password_confirm: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin_user = Depends(admin_required)
):
    """
    Handle form submission for updating a user
    Only accessible by admin users
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Check if trying to deactivate the last admin user
    if not is_admin and user.is_admin:
        # Count active admins
        admin_count = db.query(User).filter(User.is_admin == True, User.is_active == True).count()
        if admin_count <= 1:
            return templates.TemplateResponse(
                "user_detail.html",
                {
                    "request": request,
                    "title": f"Usuario: {user.username}",
                    "user": user,
                    "error": "No se puede quitar permisos de administrador al último admin activo",
                    "current_user": admin_user
                }
            )
    
    # Check password if provided
    if password:
        if password != password_confirm:
            return templates.TemplateResponse(
                "user_detail.html",
                {
                    "request": request,
                    "title": f"Usuario: {user.username}",
                    "user": user,
                    "error": "Las contraseñas no coinciden",
                    "current_user": admin_user
                }
            )
        user.password = password
    
    # Update other fields
    user.email = email
    user.fullname = fullname
    user.is_admin = is_admin
    user.is_active = is_active
    
    db.commit()
    logger.info(f"Usuario {user.username} actualizado por {admin_user['username']}")
    
    return RedirectResponse(
        url=f"/ui/users/{user_id}?success=Usuario actualizado correctamente", 
        status_code=status.HTTP_302_FOUND
    )

@router.post("/{user_id}/delete", response_class=HTMLResponse)
async def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin_user = Depends(admin_required)
):
    """
    Handle form submission for deleting a user
    Only accessible by admin users
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Prevent deleting yourself
    if user.id == admin_user['user_id']:
        return templates.TemplateResponse(
            "user_detail.html",
            {
                "request": request,
                "title": f"Usuario: {user.username}",
                "user": user,
                "error": "No puedes eliminar tu propio usuario",
                "current_user": admin_user
            }
        )
    
    # Check if trying to delete the last admin user
    if user.is_admin:
        # Count active admins
        admin_count = db.query(User).filter(User.is_admin == True, User.is_active == True).count()
        if admin_count <= 1:
            return templates.TemplateResponse(
                "user_detail.html",
                {
                    "request": request,
                    "title": f"Usuario: {user.username}",
                    "user": user,
                    "error": "No se puede eliminar el último administrador activo",
                    "current_user": admin_user
                }
            )
    
    # Delete the user
    db.delete(user)
    db.commit()
    logger.info(f"Usuario {user.username} eliminado por {admin_user['username']}")
    
    return RedirectResponse(
        url="/ui/users/?success=Usuario eliminado correctamente", 
        status_code=status.HTTP_302_FOUND
    )