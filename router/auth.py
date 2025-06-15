# router/auth.py - Router de autenticación con soporte AD

from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
from sqlalchemy.orm import Session
import os

from models.database import get_db
from models.models import User
from utils.auth_enhanced import auth_service

# Setup logging
logger = logging.getLogger(__name__)

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["authentication"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/"):
    """Página de login con soporte para múltiples proveedores"""
    
    # Verificar si ya está autenticado
    session_id = request.cookies.get("session")
    if session_id:
        session_data = auth_service.verify_session(session_id)
        if session_data:
            return RedirectResponse(url=next, status_code=302)
    
    # Configuración para mostrar en la plantilla
    ad_enabled = os.getenv('AD_SYNC_ENABLED', 'false').lower() == 'true'
    ad_server = os.getenv('AD_SERVER', 'N/A') if ad_enabled else None
    
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request, 
            "title": "Iniciar Sesión", 
            "next": next,
            "ad_enabled": ad_enabled,
            "ad_server": ad_server,
            "error": request.query_params.get("error")
        }
    )

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db)
):
    """Maneja el login con soporte para múltiples proveedores"""
    
    try:
        # Intentar autenticación con el servicio mejorado
        success, user, message = auth_service.authenticate_user(db, username, password)
        
        if success and user:
            # Crear token de acceso
            token_data = auth_service.create_access_token(user)
            
            # Configurar cookie de sesión
            response = RedirectResponse(url=next, status_code=302)
            response.set_cookie(
                key="session",
                value=token_data["access_token"],
                httponly=True,
                max_age=86400,  # 24 horas
                path="/",
                secure=False  # Cambiar a True en producción con HTTPS
            )
            
            logger.info(f"Login exitoso: {username} (proveedor: {user.auth_provider})")
            return response
        else:
            # Error de autenticación
            logger.warning(f"Login fallido para: {username} - {message}")
            
            error_url = f"/login?error={message}&next={next}"
            return RedirectResponse(url=error_url, status_code=302)
            
    except Exception as e:
        logger.error(f"Error inesperado en login: {str(e)}")
        error_url = f"/login?error=Error interno del servidor&next={next}"
        return RedirectResponse(url=error_url, status_code=302)

@router.post("/api/login")
async def api_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """API endpoint para login (para AJAX)"""
    
    try:
        # Intentar autenticación
        success, user, message = auth_service.authenticate_user(db, username, password)
        
        if success and user:
            # Crear token de acceso
            token_data = auth_service.create_access_token(user)
            
            logger.info(f"API Login exitoso: {username} (proveedor: {user.auth_provider})")
            
            return JSONResponse({
                "success": True,
                "message": f"Bienvenido, {user.fullname or user.username}",
                "auth_provider": user.auth_provider,
                "redirect_url": "/",
                **token_data
            })
        else:
            logger.warning(f"API Login fallido para: {username} - {message}")
            
            return JSONResponse({
                "success": False,
                "message": message,
                "auth_provider": None
            }, status_code=401)
            
    except Exception as e:
        logger.error(f"Error en API login: {str(e)}")
        return JSONResponse({
            "success": False,
            "message": "Error interno del servidor"
        }, status_code=500)

@router.get("/logout")
async def logout(request: Request, response: Response):
    """Maneja el logout"""
    
    # Obtener session ID
    session_id = request.cookies.get("session")
    
    if session_id:
        # Revocar sesión
        auth_service.revoke_session(session_id)
        logger.info(f"Sesión revocada: {session_id[:10]}...")
    
    # Eliminar cookie y redirigir
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="session", path="/")
    
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    """Página de perfil del usuario"""
    
    # Verificar autenticación
    session_id = request.cookies.get("session")
    session_data = auth_service.verify_session(session_id)
    
    if not session_data:
        return RedirectResponse(url="/login?next=/profile", status_code=302)
    
    # Obtener datos actualizados del usuario
    user = db.query(User).filter(User.id == session_data["user_id"]).first()
    
    if not user:
        return RedirectResponse(url="/login?error=Usuario no encontrado", status_code=302)
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "title": "Mi Perfil",
            "user": user,
            "session_data": session_data
        }
    )

@router.get("/test-auth")
async def test_auth(request: Request):
    """Endpoint para probar autenticación (desarrollo)"""
    
    session_id = request.cookies.get("session")
    session_data = auth_service.verify_session(session_id)
    
    return JSONResponse({
        "authenticated": bool(session_data),
        "session_id": session_id[:10] + "..." if session_id else None,
        "session_data": {
            "user_id": session_data.get("user_id"),
            "username": session_data.get("username"),
            "is_admin": session_data.get("is_admin"),
            "auth_provider": session_data.get("auth_provider"),
            "expires_at": session_data.get("expires_at").isoformat() if session_data and session_data.get("expires_at") else None
        } if session_data else None
    })

@router.get("/access-denied", response_class=HTMLResponse)
async def access_denied(request: Request):
    """Página de acceso denegado"""
    
    session_id = request.cookies.get("session")
    session_data = auth_service.verify_session(session_id)
    
    return templates.TemplateResponse(
        "access_denied.html", 
        {
            "request": request, 
            "title": "Acceso Denegado",
            "user": session_data
        }
    )