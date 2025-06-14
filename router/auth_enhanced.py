# router/auth_enhanced.py - Router de autenticación mejorado

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
import logging

from models.database import get_db
from models.models import User
from utils.auth_enhanced import auth_service
from config.ad_config import ad_settings

logger = logging.getLogger(__name__)

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/ui",
    tags=["authentication"]
)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login con soporte para múltiples proveedores"""
    return templates.TemplateResponse(
        "login_enhanced.html",
        {
            "request": request,
            "title": "Iniciar Sesión",
            "ad_enabled": ad_settings.AD_SYNC_ENABLED,
            "ad_server": ad_settings.AD_SERVER if ad_settings.AD_SYNC_ENABLED else None
        }
    )

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Endpoint de login con soporte para múltiples proveedores"""
    try:
        # Intentar autenticación
        success, user, message = auth_service.authenticate_user(db, username, password)
        
        if not success or not user:
            logger.warning(f"Intento de login fallido para: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=message or "Credenciales inválidas"
            )
        
        # Crear token de acceso
        token_data = auth_service.create_access_token(user)
        
        logger.info(f"Login exitoso: {username} ({user.auth_provider})")
        
        return JSONResponse({
            "success": True,
            "message": f"Bienvenido, {user.fullname or user.username}",
            "auth_provider": user.auth_provider,
            **token_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login de {username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.get("/logout")
async def logout():
    """Endpoint de logout"""
    # El logout se maneja principalmente en el frontend
    # eliminando el token del localStorage
    return RedirectResponse(
        url="/ui/login?message=Sesión cerrada correctamente",
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.post("/api/validate-token")
async def validate_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """Valida un token JWT"""
    try:
        # Extraer token del header Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token requerido"
            )
        
        token = auth_header.split(" ")[1]
        user = auth_service.get_current_user(db, token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )
        
        return JSONResponse({
            "valid": True,
            "user": user.to_dict()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando token: {str(e)}")
        return JSONResponse({
            "valid": False,
            "error": "Error validando token"
        }, status_code=status.HTTP_401_UNAUTHORIZED)