# app/router/ui_auth.py

from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from models.database import get_db
from utils.auth import get_current_user, create_access_token
import os

# Configurar templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(
    prefix="/ui",
    tags=["ui_auth"]
)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Página de inicio de sesión
    """
    return templates.TemplateResponse("login.html", {"request": request, "title": "Iniciar Sesión"})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Página de registro de usuario
    """
    return templates.TemplateResponse("register.html", {"request": request, "title": "Crear Cuenta"})

@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """
    Cierra la sesión del usuario (frontend)
    """
    # La sesión se maneja en el lado del cliente (localStorage)
    # Solo necesitamos mostrar una página de confirmación
    return templates.TemplateResponse(
        "message.html", 
        {
            "request": request, 
            "title": "Sesión Cerrada", 
            "message": "Has cerrado sesión correctamente", 
            "type": "success",
            "redirect_url": "/ui/login",
            "redirect_text": "Volver a Iniciar Sesión",
            "auto_redirect": 2 # Redireccionar después de 2 segundos
        }
    )

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Página de registro de usuario
    """
    return templates.TemplateResponse("register.html", {"request": request, "title": "Crear Cuenta"})


async def check_auth(request: Request):
    """
    Verifica si el usuario está autenticado mediante cookie o token en header.
    
    Esta función se usa como un middleware en cada ruta que requiera autenticación.
    Devuelve una redirección a la página de login si el usuario no está autenticado.
    """
    # Comprobar si la ruta está en la lista de rutas públicas
    public_routes = ['/ui/login', '/ui/register', '/ui/logout', '/static/', '/docs', '/redoc', '/openapi.json']
    
    # Permitir acceso a rutas públicas
    for route in public_routes:
        if request.url.path.startswith(route):
            return None
    
    # Para rutas protegidas, verificar autenticación
    auth_header = request.headers.get('Authorization')
    
    # Si no hay header de autorización, redireccionar a login
    if not auth_header or not auth_header.startswith('Bearer '):
        return RedirectResponse(url='/ui/login', status_code=302)
    
    # Extraer token
    token = auth_header.replace('Bearer ', '')
    
    # Validar token (esto se hace en cada endpoint protegido con get_current_user)
    # Aquí solo verificamos si existe
    if not token:
        return RedirectResponse(url='/ui/login', status_code=302)
    
    # Si llegamos aquí, existe un token. La validación detallada se hace en cada endpoint
    return None

# Este middleware se debe agregar en la aplicación principal
def add_auth_middleware(app):
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # Verificar autenticación para rutas de UI
        if request.url.path.startswith('/ui/'):
            redirect_response = await check_auth(request)
            if redirect_response:
                return redirect_response
        
        # Continuar con la solicitud
        response = await call_next(request)
        return response