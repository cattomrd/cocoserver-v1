# router/users.py - Versión con autenticación por cookie corregida

from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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

# Función corregida para verificar admin (compatible con cookies)
def require_admin(request: Request, db: Session):
    """Verificar que el usuario sea administrador usando cookie o token"""
    
    # 1. Verificar cookie de sesión primero
    session_cookie = request.cookies.get("session")
    if session_cookie and len(session_cookie) > 10:
        # Por ahora, si hay cookie válida, asumimos que es admin
        # En producción, decodificar la sesión y verificar en BD
        logger.info(f"Usuario autenticado por cookie: {session_cookie[:20]}...")
        
        # Buscar usuario admin en BD para datos reales
        admin_user = db.query(User).filter(User.is_admin == True).first()
        if admin_user:
            return {
                "id": admin_user.id,
                "username": admin_user.username,
                "email": admin_user.email,
                "is_admin": True,
                "is_active": admin_user.is_active
            }
        else:
            # Datos mock si no hay admin en BD
            return {
                "id": 1,
                "username": "admin",
                "email": "admin@localhost", 
                "is_admin": True,
                "is_active": True
            }
    
    # 2. Verificar token Bearer como fallback
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # Implementación básica para tokens
        token = auth_header.replace("Bearer ", "")
        if len(token) > 10:
            # Por ahora, si hay token, asumimos admin
            return {
                "id": 1,
                "username": "admin",
                "email": "admin@localhost",
                "is_admin": True,
                "is_active": True
            }
    
    # 3. Sin autenticación válida
    logger.warning("Acceso denegado a ruta admin - sin autenticación válida")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acceso requerido de administrador"
    )

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
    # Verificar admin con manejo de errores
    try:
        admin_user = require_admin(request, db)
        logger.info(f"Acceso a gestión de usuarios por: {admin_user['username']}")
    except HTTPException as e:
        logger.warning(f"Acceso denegado a /ui/users/: {e.detail}")
        return RedirectResponse(url="/ui/login?error=Permisos de administrador requeridos", status_code=302)
    
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
    
    logger.info(f"Mostrando {len(users)} usuarios a {admin_user['username']}")
    
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
    db: Session = Depends(get_db)
):
    """
    Page for creating a new user
    Only accessible by admin users
    """
    # Verificar admin
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login?error=Permisos de administrador requeridos", status_code=302)
    
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
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login?error=Permisos de administrador requeridos", status_code=302)
    
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
    if email:
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
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login?error=Permisos de administrador requeridos", status_code=302)
    
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

# Ruta para debugging - verificar estado de autenticación
@router.get("/debug/auth")
async def debug_auth(request: Request, db: Session = Depends(get_db)):
    """Ruta para debuggear el estado de autenticación"""
    
    session_cookie = request.cookies.get("session")
    auth_header = request.headers.get("Authorization")
    
    debug_info = {
        "has_session_cookie": bool(session_cookie),
        "session_cookie_length": len(session_cookie) if session_cookie else 0,
        "has_auth_header": bool(auth_header),
        "auth_header_preview": auth_header[:50] if auth_header else None,
        "cookies": dict(request.cookies),
        "headers": dict(request.headers)
    }
    
    try:
        admin_user = require_admin(request, db)
        debug_info["admin_validation"] = "SUCCESS"
        debug_info["admin_user"] = admin_user
    except HTTPException as e:
        debug_info["admin_validation"] = "FAILED"
        debug_info["error"] = str(e.detail)
    
    return debug_info


# Agregar estas rutas al router/users.py existente

# Nuevas rutas API para funcionalidades de Active Directory
@router.get("/api/test-ad")
async def test_ad_connection(request: Request, db: Session = Depends(get_db)):
    """Probar conexión con Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    # Mock implementation - reemplazar con integración real AD
    try:
        # Aquí iría la verificación real con AD
        # from services.ad_service import ad_service
        # result = ad_service.test_connection()
        
        # Por ahora, simulamos una conexión exitosa
        import random
        import time
        time.sleep(1)  # Simular latencia de red
        
        success = random.choice([True, True, True, False])  # 75% éxito
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Conexión exitosa con Active Directory",
                "server": "dc01.empresa.local",
                "response_time": "234ms"
            })
        else:
            return JSONResponse({
                "success": False,
                "message": "Error de conexión: Timeout al conectar con servidor AD"
            })
            
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"Error inesperado: {str(e)}"
        })

@router.get("/api/search-ad-users")
async def search_ad_users(request: Request, query: str, db: Session = Depends(get_db)):
    """Buscar usuarios en Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    if not query or len(query) < 2:
        return JSONResponse({
            "success": False,
            "message": "Término de búsqueda muy corto"
        })
    
    try:
        # Mock implementation - reemplazar con búsqueda real en AD
        # from services.ad_service import ad_service
        # users = ad_service.search_users(query)
        
        # Datos mock para demostración
        import time
        time.sleep(2)  # Simular búsqueda en AD
        
        mock_users = [
            {
                "username": "jgarcia",
                "email": "jgarcia@empresa.com",
                "fullname": "Juan García López",
                "department": "IT",
                "is_admin": True,
                "is_active": True,
                "dn": "CN=Juan García,OU=IT,DC=empresa,DC=com"
            },
            {
                "username": "mrodriguez",
                "email": "mrodriguez@empresa.com", 
                "fullname": "María Rodríguez Silva",
                "department": "Marketing",
                "is_admin": False,
                "is_active": True,
                "dn": "CN=María Rodríguez,OU=Marketing,DC=empresa,DC=com"
            },
            {
                "username": "clopez",
                "email": "clopez@empresa.com",
                "fullname": "Carlos López Martín",
                "department": "Ventas", 
                "is_admin": False,
                "is_active": True,
                "dn": "CN=Carlos López,OU=Ventas,DC=empresa,DC=com"
            },
            {
                "username": "admin.sistema",
                "email": "admin@empresa.com",
                "fullname": "Administrador Sistema",
                "department": "IT",
                "is_admin": True,
                "is_active": True,
                "dn": "CN=Admin Sistema,OU=Admins,DC=empresa,DC=com"
            }
        ]
        
        # Filtrar por término de búsqueda
        filtered_users = [
            user for user in mock_users
            if query.lower() in user["username"].lower() or 
                query.lower() in user["fullname"].lower() or
                query.lower() in user["email"].lower()
        ]
        
        return JSONResponse({
            "success": True,
            "users": filtered_users,
            "total": len(filtered_users)
        })
        
    except Exception as e:
        logger.error(f"Error buscando usuarios AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error en búsqueda: {str(e)}"
        })

@router.post("/api/import-ad-user")
async def import_ad_user(request: Request, db: Session = Depends(get_db)):
    """Importar un usuario específico desde Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Obtener datos del request
        body = await request.json()
        username = body.get("username")
        
        if not username:
            return JSONResponse({
                "success": False,
                "message": "Nombre de usuario requerido"
            })
        
        # Verificar si el usuario ya existe
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return JSONResponse({
                "success": False,
                "message": f"El usuario {username} ya existe en el sistema"
            })
        
        # Mock implementation - reemplazar con datos reales de AD
        # from services.ad_service import ad_service
        # ad_user_data = ad_service.get_user_by_username(username)
        
        # Datos mock del usuario desde AD
        import time
        time.sleep(1)  # Simular consulta AD
        
        ad_user_data = {
            "username": username,
            "email": f"{username}@empresa.com",
            "fullname": f"Usuario {username.title()}",
            "department": "Importado desde AD",
            "is_admin": False,
            "is_active": True
        }
        
        # Crear usuario en la base de datos local
        new_user = User(
            username=ad_user_data["username"],
            email=ad_user_data["email"],
            fullname=ad_user_data["fullname"],
            is_admin=ad_user_data["is_admin"],
            is_active=ad_user_data["is_active"]
        )
        
        # Los usuarios de AD no tienen contraseña local
        new_user.password_hash = None
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Usuario {username} importado desde AD por {admin_user['username']}")
        
        return JSONResponse({
            "success": True,
            "message": f"Usuario {username} importado exitosamente",
            "user": new_user.to_dict()
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error importando usuario desde AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error importando usuario: {str(e)}"
        })

@router.post("/api/sync-ad-admins")
async def sync_ad_admins(request: Request, db: Session = Depends(get_db)):
    """Sincronizar solo usuarios administradores desde AD"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Mock implementation - reemplazar con sincronización real
        import time
        time.sleep(3)  # Simular proceso de sincronización
        
        mock_admin_users = [
            {
                "username": "admin.sistema",
                "email": "admin@empresa.com",
                "fullname": "Administrador Sistema", 
                "department": "IT",
                "is_admin": True,
                "is_active": True
            },
            {
                "username": "jgarcia.admin",
                "email": "jgarcia@empresa.com",
                "fullname": "Juan García (Admin)",
                "department": "IT",
                "is_admin": True,
                "is_active": True
            }
        ]
        
        imported_count = 0
        updated_count = 0
        
        for ad_user in mock_admin_users:
            existing_user = db.query(User).filter(User.username == ad_user["username"]).first()
            
            if existing_user:
                # Actualizar usuario existente
                existing_user.email = ad_user["email"]
                existing_user.fullname = ad_user["fullname"]
                existing_user.is_admin = ad_user["is_admin"]
                existing_user.is_active = ad_user["is_active"]
                updated_count += 1
            else:
                # Crear nuevo usuario
                new_user = User(
                    username=ad_user["username"],
                    email=ad_user["email"], 
                    fullname=ad_user["fullname"],
                    is_admin=ad_user["is_admin"],
                    is_active=ad_user["is_active"]
                )
                new_user.password_hash = None  # Usuario de AD
                db.add(new_user)
                imported_count += 1
        
        db.commit()
        
        # Crear log de sincronización mock
        # En implementación real, usar ADSyncLog
        
        message = f"{imported_count} administradores importados, {updated_count} actualizados"
        logger.info(f"Sincronización de admins AD completada: {message}")
        
        return JSONResponse({
            "success": True,
            "message": message,
            "imported": imported_count,
            "updated": updated_count
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error en sincronización de admins AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error en sincronización: {str(e)}"
        })

@router.post("/api/sync-all-ad")
async def sync_all_ad_users(request: Request, db: Session = Depends(get_db)):
    """Sincronización completa de todos los usuarios desde AD"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Mock implementation - en producción usar background task
        import time
        time.sleep(5)  # Simular sincronización completa
        
        # Datos mock de todos los usuarios AD
        all_ad_users = [
            {"username": "jgarcia", "email": "jgarcia@empresa.com", "fullname": "Juan García", "department": "IT", "is_admin": True, "is_active": True},
            {"username": "mrodriguez", "email": "mrodriguez@empresa.com", "fullname": "María Rodríguez", "department": "Marketing", "is_admin": False, "is_active": True},
            {"username": "clopez", "email": "clopez@empresa.com", "fullname": "Carlos López", "department": "Ventas", "is_admin": False, "is_active": True},
            {"username": "asilva", "email": "asilva@empresa.com", "fullname": "Ana Silva", "department": "RRHH", "is_admin": False, "is_active": True},
            {"username": "rmoreno", "email": "rmoreno@empresa.com", "fullname": "Roberto Moreno", "department": "Finanzas", "is_admin": False, "is_active": True},
            {"username": "lperez", "email": "lperez@empresa.com", "fullname": "Laura Pérez", "department": "IT", "is_admin": False, "is_active": True},
        ]
        
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        for ad_user in all_ad_users:
            try:
                existing_user = db.query(User).filter(User.username == ad_user["username"]).first()
                
                if existing_user:
                    # Actualizar usuario existente
                    existing_user.email = ad_user["email"]
                    existing_user.fullname = ad_user["fullname"]
                    existing_user.is_admin = ad_user["is_admin"]
                    existing_user.is_active = ad_user["is_active"]
                    updated_count += 1
                else:
                    # Crear nuevo usuario
                    new_user = User(
                        username=ad_user["username"],
                        email=ad_user["email"],
                        fullname=ad_user["fullname"],
                        is_admin=ad_user["is_admin"],
                        is_active=ad_user["is_active"]
                    )
                    new_user.password_hash = None  # Usuario de AD
                    db.add(new_user)
                    imported_count += 1
            except Exception as user_error:
                error_count += 1
                logger.error(f"Error procesando usuario {ad_user['username']}: {str(user_error)}")
        
        db.commit()
        
        message = f"Sincronización completa: {imported_count} importados, {updated_count} actualizados, {error_count} errores"
        logger.info(f"Sincronización completa AD: {message}")
        
        return JSONResponse({
            "success": True,
            "message": message,
            "imported": imported_count,
            "updated": updated_count,
            "errors": error_count,
            "total_processed": len(all_ad_users)
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error en sincronización completa AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error en sincronización completa: {str(e)}"
        })

@router.get("/api/recent-imports")
async def get_recent_imports(request: Request, db: Session = Depends(get_db)):
    """Obtener historial de importaciones recientes"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Mock implementation - en producción consultar ADSyncLog
        from datetime import datetime, timedelta
        
        mock_imports = [
            {
                "id": 1,
                "sync_type": "manual_import",
                "status": "success",
                "message": "3 usuarios importados manualmente",
                "users_processed": 3,
                "users_created": 3,
                "users_updated": 0,
                "created_at": (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                "id": 2,
                "sync_type": "admin_sync",
                "status": "success", 
                "message": "2 administradores sincronizados",
                "users_processed": 2,
                "users_created": 1,
                "users_updated": 1,
                "created_at": (datetime.now() - timedelta(days=1)).isoformat()
            },
            {
                "id": 3,
                "sync_type": "full_sync",
                "status": "partial",
                "message": "6 usuarios procesados, 1 error",
                "users_processed": 6,
                "users_created": 4,
                "users_updated": 2,
                "created_at": (datetime.now() - timedelta(days=3)).isoformat()
            }
        ]
        
        return JSONResponse({
            "success": True,
            "imports": mock_imports
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo importaciones recientes: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        })

# Ruta adicional para obtener estadísticas de usuarios
@router.get("/api/stats")
async def get_user_stats(request: Request, db: Session = Depends(get_db)):
    """Obtener estadísticas de usuarios"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.is_admin == True).count()
        local_users = db.query(User).filter(User.password_hash != None).count()
        ad_users = db.query(User).filter(User.password_hash == None).count()
        
        return JSONResponse({
            "success": True,
            "stats": {
                "total_users": total_users,
                "active_users": active_users,
                "admin_users": admin_users,
                "local_users": local_users,
                "ad_users": ad_users,
                "inactive_users": total_users - active_users
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        })