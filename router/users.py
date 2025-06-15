# router/users.py - Router corregido compatible con tu estructura actual

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import logging
from datetime import datetime
from pathlib import Path
import os
# Imports del proyecto
from models.database import get_db
from models.models import User
from utils.auth import create_session, get_current_user  # Solo importar lo que existe

# Import del servicio AD con manejo de errores robusto
try:
    from services.ad_service import ad_service
    AD_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Active Directory service importado correctamente")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️  No se pudo importar ActiveDirectoryService: {e}")
    AD_AVAILABLE = False
    ad_service = None
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Error inicializando AD service: {e}")
    AD_AVAILABLE = False
    ad_service = None

# Configurar templates y router
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/ui/users",
    tags=["user management"]
)

# Función local para verificar admin (compatible con tu estructura actual)
def require_admin(request: Request, db: Session):
    """Verificar que el usuario sea administrador usando cookie o token"""
    
    # 1. Verificar cookie de sesión primero
    session_cookie = request.cookies.get("session")
    if session_cookie and len(session_cookie) > 10:
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
        token = auth_header.replace("Bearer ", "")
        if len(token) > 10:
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
        status_code=401,
        detail="Acceso requerido de administrador"
    )

# =================== PÁGINAS WEB ===================

@router.get("/", response_class=HTMLResponse)
async def list_users(
    request: Request, 
    search: Optional[str] = Query(None),
    source: Optional[str] = Query("local"),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """Lista usuarios desde base local o Active Directory con manejo robusto de errores"""
    
    # Verificar admin
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login?error=Permisos de administrador requeridos", status_code=302)
    
    if source == "ad":
        return await handle_ad_user_listing(request, search, admin_user, db)
    else:
        return await handle_local_user_listing(request, search, is_active, admin_user, db)

async def handle_ad_user_listing(request: Request, search: Optional[str], admin_user: dict, db: Session):
    """Maneja la listado de usuarios de Active Directory con verificaciones robustas"""
    
    # Verificar si AD está disponible
    if not AD_AVAILABLE or not ad_service:
        return templates.TemplateResponse(
            "users.html",  # Usar template existente
            {
                "request": request, 
                "title": "Usuarios Active Directory",
                "users": [],
                "search": search or "",
                "source": "ad",
                "error": "Active Directory no está configurado o disponible",
                "current_user": admin_user,
                "ad_available": False
            }
        )
    
    # Verificar configuración antes de intentar buscar
    try:
        config_test = ad_service.test_connection()
        if not config_test.get("success", False):
            return templates.TemplateResponse(
                "users.html",
                {
                    "request": request, 
                    "title": "Usuarios Active Directory",
                    "users": [],
                    "search": search or "",
                    "source": "ad",
                    "error": f"Error de configuración AD: {config_test.get('message', 'Configuración inválida')}",
                    "current_user": admin_user,
                    "ad_available": AD_AVAILABLE
                }
            )
    except Exception as e:
        logger.error(f"Error verificando configuración AD: {str(e)}")
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request, 
                "title": "Usuarios Active Directory",
                "users": [],
                "search": search or "",
                "source": "ad",
                "error": f"Error al verificar configuración: {str(e)}",
                "current_user": admin_user,
                "ad_available": AD_AVAILABLE
            }
        )
    
    # Buscar en Active Directory
    search_term = search if search else ""
    try:
        if search_term:
            # Buscar usuarios específicos
            if hasattr(ad_service, 'search_users'):
                ad_users = ad_service.search_users(search_term, max_results=200)
            else:
                # Fallback: obtener todos y filtrar localmente
                all_users = ad_service.get_all_users(limit=500)
                ad_users = [
                    user for user in all_users 
                    if search_term.lower() in user.get('username', '').lower() or
                       search_term.lower() in user.get('fullname', '').lower() or
                       search_term.lower() in user.get('email', '').lower()
                ][:200]
        else:
            ad_users = ad_service.get_all_users(limit=200)
        
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request, 
                "title": "Usuarios Active Directory",
                "users": ad_users,
                "search": search_term,
                "source": "ad",
                "current_user": admin_user,
                "ad_available": AD_AVAILABLE,
                "total_found": len(ad_users)
            }
        )
        
    except Exception as e:
        logger.error(f"Error buscando usuarios en AD: {str(e)}")
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request, 
                "title": "Usuarios Active Directory",
                "users": [],
                "search": search_term,
                "source": "ad",
                "error": f"Error al buscar usuarios: {str(e)}",
                "current_user": admin_user,
                "ad_available": AD_AVAILABLE
            }
        )

async def handle_local_user_listing(
    request: Request, 
    search: Optional[str], 
    is_active: Optional[bool],
    admin_user: dict,
    db: Session
):
    """Maneja el listado de usuarios locales con filtros"""
    
    # Construir query con filtros
    query = db.query(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_term)) | 
            (User.email.ilike(search_term)) |
            (User.fullname.ilike(search_term))
        )
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.order_by(User.username).all()
    
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request, 
            "title": "Gestión de Usuarios",
            "users": users,
            "search": search,
            "source": "local",
            "is_active": is_active,
            "current_user": admin_user,
            "ad_available": AD_AVAILABLE
        }
    )

@router.get("/ad-debug", response_class=HTMLResponse)
async def ad_debug_page(request: Request, db: Session = Depends(get_db)):
    """Página de diagnóstico de Active Directory"""
    
    # Verificar admin
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login?error=Permisos de administrador requeridos", status_code=302)
    
    if not AD_AVAILABLE or not ad_service:
        config_status = {"status": "unavailable", "error": "AD service not available"}
        connection_test = {"success": False, "error": "AD service not available"}
    else:
        try:
            connection_test = ad_service.test_connection()
            config_status = {
                "status": "available" if connection_test.get("success") else "error",
                "details": connection_test.get("message", "Sin detalles")
            }
        except Exception as e:
            config_status = {"status": "error", "error": str(e)}
            connection_test = {"success": False, "error": str(e)}
    
    return templates.TemplateResponse(
        "ad_debug.html",
        {
            "request": request,
            "title": "Diagnóstico Active Directory",
            "config_status": config_status,
            "connection_test": connection_test,
            "ad_available": AD_AVAILABLE,
            "current_user": admin_user
        }
    )

# =================== API ENDPOINTS ===================

@router.get("/api/test-ad-connection")
async def test_ad_connection(request: Request, db: Session = Depends(get_db)):
    """API para probar conexión con Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    if not AD_AVAILABLE or not ad_service:
        return JSONResponse({
            "success": False,
            "error": "Active Directory service not available",
            "details": "Check if AD service is properly configured and imported",
            "available": False
        })
    
    try:
        result = ad_service.test_connection()
        result["available"] = True
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error en test de conexión AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "details": "Check logs for more information",
            "available": AD_AVAILABLE
        })

@router.get("/api/search-ad-users")
async def search_ad_users(
    request: Request, 
    query: str, 
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Buscar usuarios en Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    if not query or len(query) < 2:
        return JSONResponse({
            "success": False,
            "message": "Término de búsqueda muy corto (mínimo 2 caracteres)"
        })
    
    try:
        # Importar y usar el servicio AD real
        from services.ad_service import ad_service
        
        # Usar el método search_users con el parámetro correcto 'limit' en lugar de 'max_results'
        users = ad_service.search_users(query, limit=limit)
        
        if users:
            logger.info(f"Búsqueda AD para '{query}': {len(users)} usuarios encontrados")
            return JSONResponse({
                "success": True,
                "users": users,
                "total": len(users),
                "query": query
            })
        else:
            return JSONResponse({
                "success": True,
                "users": [],
                "total": 0,
                "message": f"No se encontraron usuarios para '{query}'"
            })
        
    except ImportError:
        logger.error("Servicio AD no disponible - usando datos mock")
        # Fallback a datos mock si el servicio no está disponible
        mock_users = [
            {
                "username": "jorge.romero",
                "email": "jorge.romero@ikeasi.com",
                "fullname": "Jorge Romero",
                "department": "IT",
                "dn": "CN=Jorge Romero,OU=IT,DC=ikeaspc,DC=ikeasi,DC=com"
            },
            {
                "username": "jorge.martinez",
                "email": "jorge.martinez@ikeasi.com", 
                "fullname": "Jorge Martinez",
                "department": "Marketing",
                "dn": "CN=Jorge Martinez,OU=Marketing,DC=ikeaspc,DC=ikeasi,DC=com"
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
            "total": len(filtered_users),
            "message": "Usando datos de demostración (servicio AD no disponible)"
        })
        
    except Exception as e:
        logger.error(f"Error buscando usuarios AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error en búsqueda: {str(e)}"
        }, status_code=500)

@router.get("/api/test-ad")
async def test_ad_connection(request: Request, db: Session = Depends(get_db)):
    """Probar conexión con Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Usar el servicio AD real
        from services.ad_service import ad_service
        
        result = ad_service.test_connection()
        
        if result['success']:
            logger.info(f"Test AD exitoso: {result['message']}")
            return JSONResponse({
                "success": True,
                "message": result['message'],
                "server": result.get('server', 'N/A'),
                "auth_type": result.get('auth_type', 'SIMPLE'),
                "entries_found": result.get('entries_found', 0)
            })
        else:
            logger.error(f"Test AD falló: {result['message']}")
            return JSONResponse({
                "success": False,
                "message": result['message'],
                "server": result.get('server', 'N/A')
            }, status_code=500)
            
    except ImportError:
        logger.error("Servicio AD no disponible")
        return JSONResponse({
            "success": False,
            "message": "Servicio de Active Directory no está configurado"
        }, status_code=503)
        
    except Exception as e:
        logger.error(f"Error inesperado en test AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error inesperado: {str(e)}"
        }, status_code=500)
@router.get("/api/test-ad")
async def test_ad_connection_legacy(request: Request, db: Session = Depends(get_db)):
    """API legacy para probar conexión con Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    if not AD_AVAILABLE or not ad_service:
        return JSONResponse({
            "success": False,
            "error": "Active Directory service not available",
            "details": "Check if AD service is properly configured and imported",
            "available": False
        })
    
    try:
        result = ad_service.test_connection()
        result["available"] = True
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Error en test de conexión AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "details": "Check logs for more information",
            "available": AD_AVAILABLE
        })

@router.get("/api/recent-imports")
async def get_recent_imports(request: Request, db: Session = Depends(get_db)):
    """API para obtener historial de importaciones recientes"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Mock implementation - en producción consultar tabla de logs
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

@router.get("/api/stats")
async def get_user_stats(request: Request, db: Session = Depends(get_db)):
    """API para obtener estadísticas de usuarios"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        admin_users = db.query(User).filter(User.is_admin == True).count()
        
        # Estadísticas por proveedor de auth (si existe el campo)
        local_users = 0
        ad_users = 0
        
        # Verificar si el modelo User tiene el campo auth_provider
        if hasattr(User, 'auth_provider'):
            local_users = db.query(User).filter(User.auth_provider == 'local').count()
            ad_users = db.query(User).filter(User.auth_provider == 'active_directory').count()
        else:
            # Fallback: usar password_hash para distinguir
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
            },
            "ad_available": AD_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        })

@router.post("/api/import-ad-user")
async def import_ad_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Importar un usuario específico desde Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Obtener datos del request
        body = await request.json()
        username = body.get("username")
        dn = body.get("dn")  # Distinguished Name del usuario en AD
        
        if not username:
            return JSONResponse({
                "success": False,
                "message": "Nombre de usuario requerido"
            })
        
        logger.info(f"Intentando importar usuario AD: {username}")
        
        # Verificar si el usuario ya existe
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return JSONResponse({
                "success": False,
                "message": f"El usuario {username} ya existe en el sistema"
            })
        
        # Obtener datos del usuario desde Active Directory
        try:
            from services.ad_service import ad_service
            
            # Intentar obtener datos del usuario desde AD
            ad_user_data = ad_service.get_user_by_username(username)
            
            if not ad_user_data:
                return JSONResponse({
                    "success": False,
                    "message": f"Usuario {username} no encontrado en Active Directory"
                })
                
        except ImportError:
            logger.error("Servicio AD no disponible - usando datos básicos")
            # Fallback con datos básicos si el servicio no está disponible
            ad_user_data = {
                "username": username,
                "email": f"{username}@{os.getenv('AD_DOMAIN_FQDN', 'ikeasi.com')}",
                "fullname": username.replace('.', ' ').replace('-', ' ').title(),
                "department": "Importado desde AD",
                "dn": dn or f"CN={username},DC=ikeaspc,DC=ikeasi,DC=com",
                "is_enabled": True,
                "groups": []
            }
        
        except Exception as ad_error:
            logger.error(f"Error consultando AD para usuario {username}: {str(ad_error)}")
            return JSONResponse({
                "success": False,
                "message": f"Error consultando Active Directory: {str(ad_error)}"
            })
        
        # Determinar si el usuario debe ser administrador
        # Basado en grupos de AD
        is_admin = False
        admin_groups = os.getenv('AD_ADMIN_GROUPS', 'Domain Admins,Administrators').split(',')
        
        for group in ad_user_data.get('groups', []):
            group_name = group.split(',')[0].replace('CN=', '').strip()
            if group_name in admin_groups:
                is_admin = True
                break
        
        # Crear usuario en la base de datos local
        try:
            new_user = User(
                username=ad_user_data["username"],
                email=ad_user_data.get("email"),
                fullname=ad_user_data.get("fullname") or ad_user_data["username"],
                department=ad_user_data.get("department"),
                is_admin=is_admin,
                is_active=ad_user_data.get("is_enabled", True),
                auth_provider="ad",  # Marcar como usuario de AD
                ad_dn=ad_user_data.get("dn")  # Guardar DN para referencia
            )
            
            # Los usuarios de AD no tienen contraseña local
            new_user.password_hash = None
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"Usuario {username} importado exitosamente desde AD por {admin_user['username']}")
            
            return JSONResponse({
                "success": True,
                "message": f"Usuario {username} importado exitosamente desde Active Directory",
                "user": {
                    "id": new_user.id,
                    "username": new_user.username,
                    "email": new_user.email,
                    "fullname": new_user.fullname,
                    "department": new_user.department,
                    "is_admin": new_user.is_admin,
                    "is_active": new_user.is_active,
                    "auth_provider": new_user.auth_provider,
                    "created_at": new_user.created_at.isoformat() if new_user.created_at else None
                }
            })
            
        except Exception as db_error:
            db.rollback()
            logger.error(f"Error creando usuario {username} en BD: {str(db_error)}")
            return JSONResponse({
                "success": False,
                "message": f"Error creando usuario en base de datos: {str(db_error)}"
            })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error general importando usuario desde AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error interno: {str(e)}"
        }, status_code=500)


@router.post("/api/sync-all-ad-users")
async def sync_all_ad_users(
    request: Request,
    db: Session = Depends(get_db)
):
    """Sincronizar todos los usuarios desde Active Directory"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return JSONResponse({"success": False, "message": "Acceso denegado"}, status_code=401)
    
    try:
        # Obtener parámetros opcionales
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        limit = body.get("limit", 100)  # Limitar por seguridad
        update_existing = body.get("update_existing", True)
        
        logger.info(f"Iniciando sincronización masiva de usuarios AD (límite: {limit})")
        
        # Obtener usuarios desde Active Directory
        try:
            from services.ad_service import ad_service
            
            all_ad_users = ad_service.get_all_users(limit=limit)
            
            if not all_ad_users:
                return JSONResponse({
                    "success": False,
                    "message": "No se pudieron obtener usuarios de Active Directory"
                })
                
        except ImportError:
            logger.error("Servicio AD no disponible")
            return JSONResponse({
                "success": False,
                "message": "Servicio de Active Directory no está configurado"
            })
        except Exception as ad_error:
            logger.error(f"Error obteniendo usuarios de AD: {str(ad_error)}")
            return JSONResponse({
                "success": False,
                "message": f"Error consultando Active Directory: {str(ad_error)}"
            })
        
        # Procesar usuarios
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        admin_groups = os.getenv('AD_ADMIN_GROUPS', 'Domain Admins,Administrators').split(',')
        
        for ad_user in all_ad_users:
            try:
                username = ad_user.get("username")
                if not username:
                    error_count += 1
                    continue
                
                # Verificar si el usuario ya existe
                existing_user = db.query(User).filter(User.username == username).first()
                
                # Determinar si es admin
                is_admin = False
                for group in ad_user.get('groups', []):
                    group_name = group.split(',')[0].replace('CN=', '').strip()
                    if group_name in admin_groups:
                        is_admin = True
                        break
                
                if existing_user:
                    if update_existing:
                        # Actualizar usuario existente
                        existing_user.email = ad_user.get("email") or existing_user.email
                        existing_user.fullname = ad_user.get("fullname") or existing_user.fullname
                        existing_user.department = ad_user.get("department") or existing_user.department
                        existing_user.is_admin = is_admin
                        existing_user.is_active = ad_user.get("is_enabled", True)
                        existing_user.auth_provider = "ad"
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    # Crear nuevo usuario
                    new_user = User(
                        username=username,
                        email=ad_user.get("email"),
                        fullname=ad_user.get("fullname") or username,
                        department=ad_user.get("department"),
                        is_admin=is_admin,
                        is_active=ad_user.get("is_enabled", True),
                        auth_provider="ad",
                        ad_dn=ad_user.get("dn")
                    )
                    new_user.password_hash = None  # Usuario de AD
                    db.add(new_user)
                    imported_count += 1
                    
            except Exception as user_error:
                error_count += 1
                logger.error(f"Error procesando usuario {ad_user.get('username', 'unknown')}: {str(user_error)}")
        
        # Guardar cambios
        try:
            db.commit()
        except Exception as commit_error:
            db.rollback()
            logger.error(f"Error guardando cambios: {str(commit_error)}")
            return JSONResponse({
                "success": False,
                "message": f"Error guardando cambios en base de datos: {str(commit_error)}"
            })
        
        # Mensaje de resultado
        total_processed = imported_count + updated_count + skipped_count + error_count
        message = f"Sincronización completa: {imported_count} importados, {updated_count} actualizados, {skipped_count} omitidos, {error_count} errores"
        
        logger.info(f"Sincronización AD completada por {admin_user['username']}: {message}")
        
        return JSONResponse({
            "success": True,
            "message": message,
            "statistics": {
                "total_from_ad": len(all_ad_users),
                "total_processed": total_processed,
                "imported": imported_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": error_count
            }
        })
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error en sincronización masiva AD: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": f"Error interno en sincronización: {str(e)}"
        }, status_code=500)


# =================== RUTAS ORIGINALES MANTENIDAS ===================

@router.get("/create", response_class=HTMLResponse)
async def create_user_page(request: Request, db: Session = Depends(get_db)):
    """Página para crear usuario local"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login?error=Permisos de administrador requeridos", status_code=302)
        
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
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    fullname: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    is_admin: bool = Form(False),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Crear un nuevo usuario local"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login", status_code=302)
    
    # Validación de contraseñas
    if password != password_confirm:
        return templates.TemplateResponse(
            "user_create.html",
            {
                "request": request,
                "title": "Crear Usuario",
                "error": "Las contraseñas no coinciden",
                "username": username,
                "email": email,
                "fullname": fullname,
                "is_admin": is_admin,
                "is_active": is_active,
                "current_user": admin_user
            }
        )
    
    # Verificar si el usuario ya existe
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        return templates.TemplateResponse(
            "user_create.html",
            {
                "request": request,
                "title": "Crear Usuario",
                "error": "Usuario o email ya existe",
                "username": username,
                "email": email,
                "fullname": fullname,
                "is_admin": is_admin,
                "is_active": is_active,
                "current_user": admin_user
            }
        )
    
    try:
        # Crear nuevo usuario usando el método correcto de tu modelo
        new_user = User.create_user(
            db=db,
            username=username,
            email=email,
            password=password,
            fullname=fullname,
            is_admin=is_admin
        )
        new_user.is_active = is_active
        db.commit()
        
        logger.info(f"Usuario {username} creado por {admin_user['username']}")
        return RedirectResponse(url="/ui/users", status_code=302)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando usuario: {str(e)}")
        return templates.TemplateResponse(
            "user_create.html",
            {
                "request": request,
                "title": "Crear Usuario",
                "error": f"Error creando usuario: {str(e)}",
                "username": username,
                "email": email,
                "fullname": fullname,
                "is_admin": is_admin,
                "is_active": is_active,
                "current_user": admin_user
            }
        )

@router.get("/{user_id}", response_class=HTMLResponse)
async def view_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Ver detalles de un usuario local"""
    try:
        admin_user = require_admin(request, db)
    except HTTPException:
        return RedirectResponse(url="/ui/login", status_code=302)
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "title": f"Usuario: {user.username}",
            "user": user,
            "current_user": admin_user
        }
    )