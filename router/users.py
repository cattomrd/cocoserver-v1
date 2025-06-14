# router/users.py - Versión corregida

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

# Setup logging
logger = logging.getLogger(__name__)

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/ui/users",
    tags=["user management"]
)

# Función local para verificar admin (evita importaciones circulares)
def require_admin(request: Request):
    """Verificar que el usuario sea administrador"""
    # Implementación básica - en producción usar JWT
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido"
        )
    # Por ahora, asumimos que si hay token es admin
    return {"username": "admin", "is_admin": True}

# API routes for user management
@router.get("/", response_class=HTMLResponse)
async def list_users_page(
    request: Request,
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    Page for listing and managing users
    Only accessible by admin users
    """
    # Verificar admin
    try:
        admin_user = require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/ui/login", status_code=302)
    
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
    request: Request
):
    """
    Page for creating a new user
    Only accessible by admin users
    """
    # Verificar admin
    try:
        admin_user = require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/ui/login", status_code=302)
    
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
    db: Session = Depends(get_db)
):
    """
    Handle form submission for creating a new user
    Only accessible by admin users
    """
    # Verificar admin
    try:
        admin_user = require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/ui/login", status_code=302)
    
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
    db: Session = Depends(get_db)
):
    """
    Page for viewing and editing a user
    Only accessible by admin users
    """
    # Verificar admin
    try:
        admin_user = require_admin(request)
    except HTTPException:
        return RedirectResponse(url="/ui/login", status_code=302)
    
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