# router/users_enhanced.py - Router de usuarios mejorado con soporte AD

from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
from datetime import datetime

from models.database import get_db
from models.models import User, AuthProvider, ADSyncLog
from models.schemas import UserCreate, UserUpdate, UserResponse
from utils.auth_enhanced import admin_required, get_current_user, auth_service
from services.ad_service import ad_service
from config.ad_config import ad_settings

# Setup logging
logger = logging.getLogger(__name__)

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/ui/users",
    tags=["user management"]
)

# =================== PÁGINAS WEB ===================

@router.get("/", response_class=HTMLResponse)
async def list_users_page(
    request: Request,
    db: Session = Depends(get_db),
    admin_user = Depends(admin_required),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    auth_provider: Optional[str] = None
):
    """Página para listar y gestionar usuarios con filtros mejorados"""
    # Build the query
    query = db.query(User)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) |
            (User.fullname.ilike(search_term)) |
            (User.department.ilike(search_term))
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if auth_provider:
        query = query.filter(User.auth_provider == auth_provider)
        
    # Execute the query
    users = query.order_by(User.username).all()
    
    # Obtener estadísticas
    total_users = db.query(User).count()
    ad_users = db.query(User).filter(User.auth_provider == AuthProvider.ACTIVE_DIRECTORY.value).count()
    local_users = db.query(User).filter(User.auth_provider == AuthProvider.LOCAL.value).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    return templates.TemplateResponse(
        "users_enhanced.html",
        {
            "request": request,
            "title": "Gestión de Usuarios",
            "users": users,
            "search": search,
            "is_active": is_active,
            "auth_provider": auth_provider,
            "current_user": admin_user,
            "auth_providers": [p.value for p in AuthProvider],
            "stats": {
                "total": total_users,
                "ad_users": ad_users,
                "local_users": local_users,
                "active": active_users
            },
            "ad_enabled": ad_settings.AD_SYNC_ENABLED
        }
    )

@router.get("/sync", response_class=HTMLResponse)
async def sync_users_page(
    request: Request,
    admin_user = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Página para sincronización con Active Directory"""
    # Obtener logs recientes de sincronización
    recent_logs = db.query(ADSyncLog).order_by(ADSyncLog.created_at.desc()).limit(10).all()
    
    # Verificar estado de conexión AD
    ad_status = ad_service.test_connection() if ad_settings.AD_SYNC_ENABLED else None
    
    return templates.TemplateResponse(
        "users_sync.html",
        {
            "request": request,
            "title": "Sincronización Active Directory",
            "current_user": admin_user,
            "ad_enabled": ad_settings.AD_SYNC_ENABLED,
            "ad_status": ad_status,
            "recent_logs": recent_logs,
            "ad_settings": {
                "server": ad_settings.AD_SERVER,
                "base_dn": ad_settings.AD_BASE_DN,
                "auto_create": ad_settings.AD_AUTO_CREATE_USERS,
                "update_info": ad_settings.AD_UPDATE_USER_INFO
            }
        }
    )

# =================== API ENDPOINTS ===================

@router.post("/api/sync")
async def sync_users_from_ad(
    background_tasks: BackgroundTasks,
    admin_user = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """API para sincronizar usuarios desde Active Directory"""
    if not ad_settings.AD_SYNC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sincronización AD deshabilitada"
        )
    
    # Ejecutar sincronización en background
    background_tasks.add_task(auth_service.sync_users_from_ad, db)
    
    return JSONResponse({
        "success": True,
        "message": "Sincronización iniciada en segundo plano"
    })

@router.get("/api/sync/status")
async def get_sync_status(
    admin_user = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Obtiene el estado de la última sincronización"""
    latest_log = db.query(ADSyncLog).order_by(ADSyncLog.created_at.desc()).first()
    
    if not latest_log:
        return JSONResponse({
            "success": False,
            "message": "No hay logs de sincronización"
        })
    
    return JSONResponse({
        "success": True,
        "data": {
            "sync_type": latest_log.sync_type,
            "status": latest_log.status,
            "message": latest_log.message,
            "users_processed": latest_log.users_processed,
            "users_created": latest_log.users_created,
            "users_updated": latest_log.users_updated,
            "users_errors": latest_log.users_errors,
            "duration_seconds": latest_log.duration_seconds,
            "created_at": latest_log.created_at.isoformat()
        }
    })

@router.get("/api/export")
async def export_users(
    admin_user = Depends(admin_required),
    db: Session = Depends(get_db),
    format: str = Query("csv", regex="^(csv|json)$"),
    auth_provider: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Exporta usuarios en formato CSV o JSON"""
    
    # Construir query con filtros
    query = db.query(User)
    
    if auth_provider:
        query = query.filter(User.auth_provider == auth_provider)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.order_by(User.username).all()
    
    if format == "csv":
        # Crear CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Escribir cabeceras
        writer.writerow([
            'ID', 'Usuario', 'Email', 'Nombre Completo', 'Departamento',
            'Activo', 'Administrador', 'Proveedor Auth', 'Creado',
            'Último Login', 'Última Sincronización AD'
        ])
        
        # Escribir datos
        for user in users:
            writer.writerow([
                user.id,
                user.username,
                user.email or '',
                user.fullname or '',
                user.department or '',
                'Sí' if user.is_active else 'No',
                'Sí' if user.is_admin else 'No',
                user.auth_provider,
                user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '',
                user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
                user.last_ad_sync.strftime('%Y-%m-%d %H:%M:%S') if user.last_ad_sync else ''
            ])
        
        # Preparar respuesta
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"usuarios_{timestamp}.csv"
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format == "json":
        # Crear JSON
        users_data = [user.to_dict() for user in users]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"usuarios_{timestamp}.json"
        
        return JSONResponse(
            content={
                "export_date": datetime.now().isoformat(),
                "total_users": len(users_data),
                "filters": {
                    "auth_provider": auth_provider,
                    "is_active": is_active
                },
                "users": users_data
            },
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

@router.post("/api/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    admin_user = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Activa/desactiva un usuario"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir desactivar al propio admin
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta"
        )
    
    user.is_active = not user.is_active
    user.updated_at = datetime.now()
    db.commit()
    
    action = "activado" if user.is_active else "desactivado"
    logger.info(f"Usuario {user.username} {action} por {admin_user.username}")
    
    return JSONResponse({
        "success": True,
        "message": f"Usuario {action} correctamente",
        "user": user.to_dict()
    })

@router.get("/api/test-ad")
async def test_ad_connection(admin_user = Depends(admin_required)):
    """Prueba la conexión con Active Directory"""
    if not ad_settings.AD_SYNC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active Directory deshabilitado"
        )
    
    result = ad_service.test_connection()
    
    if result['success']:
        return JSONResponse({
            "success": True,
            "message": result['message'],
            "server": result['server']
        })
    else:
        return JSONResponse({
            "success": False,
            "message": result['message'],
            "server": result['server']
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@router.get("/api/ad-users")
async def get_ad_users_preview(
    admin_user = Depends(admin_required),
    limit: int = Query(10, ge=1, le=100)
):
    """Obtiene una vista previa de usuarios de AD"""
    if not ad_settings.AD_SYNC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active Directory deshabilitado"
        )
    
    try:
        # Obtener usuarios de AD (limitado)
        ad_users = ad_service.get_all_users()
        
        if not ad_users:
            return JSONResponse({
                "success": False,
                "message": "No se pudieron obtener usuarios de AD"
            })
        
        # Limitar resultados
        preview_users = ad_users[:limit]
        
        return JSONResponse({
            "success": True,
            "total_found": len(ad_users),
            "preview_count": len(preview_users),
            "users": preview_users
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo usuarios de AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error obteniendo usuarios de AD: {str(e)}"
        }, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =================== USUARIOS LOCALES ===================

@router.get("/create", response_class=HTMLResponse)
async def create_user_page(
    request: Request,
    admin_user = Depends(admin_required)
):
    """Página para crear un nuevo usuario local"""
    return templates.TemplateResponse(
        "user_create.html",
        {
            "request": request,
            "title": "Crear Usuario",
            "current_user": admin_user
        }
    )

@router.post("/create")
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    fullname: str = Form(None),
    department: str = Form(None),
    password: str = Form(...),
    password_confirm: str = Form(...),
    is_admin: bool = Form(False),
    admin_user = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Crear un nuevo usuario local"""
    
    # Validaciones
    if password != password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden"
        )
    
    # Verificar si el usuario ya existe
    if User.get_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya existe"
        )
    
    if email and User.get_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    try:
        # Crear usuario
        user = User.create_user(
            db=db,
            username=username,
            email=email,
            password=password,
            fullname=fullname,
            department=department,
            is_admin=is_admin,
            auth_provider=AuthProvider.LOCAL.value
        )
        
        logger.info(f"Usuario local creado: {username} por {admin_user.username}")
        
        return RedirectResponse(
            url="/ui/users?message=Usuario creado correctamente",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    except Exception as e:
        logger.error(f"Error creando usuario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno creando usuario"
        )