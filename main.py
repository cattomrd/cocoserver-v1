# main.py - Versión con autenticación por cookies corregida

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import logging
import os
import uvicorn

load_dotenv()

# Importar los modelos para crear las tablas
from models import models
from models.database import engine

# Importar los routers
from router import videos, playlists, raspberry, ui, devices, device_playlists, services_enhanced as services, device_service_api
from router.auth import router as auth_router
from router.users import router as users_router
from router.playlist_checker_api import router as playlist_checker_router
from router.ui_auth import router as ui_auth_router

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Crear la aplicación FastAPI
app = FastAPI(
    title="API de Gestión de Videos",
    description="API para gestionar videos y listas de reproducción para Raspberry Pi",
    version="1.0.0"
)

# Función para verificar si el usuario está autenticado por cookie
def is_authenticated(request: Request) -> bool:
    """Verificar si el usuario tiene una sesión válida por cookie"""
    session_cookie = request.cookies.get("session")
    if session_cookie and len(session_cookie) > 10:
        # Verificación básica - en producción validar JWT o sesión en BD
        return True
    return False

# RUTAS DE REDIRECCIÓN
@app.get("/login")
async def redirect_login():
    """Redireccionar /login a /ui/login"""
    return RedirectResponse(url="/ui/login", status_code=301)

@app.get("/")
async def redirect_root(request: Request):
    """Redireccionar / según el estado de autenticación"""
    if is_authenticated(request):
        # Si está autenticado, ir al dashboard
        return RedirectResponse(url="/ui/dashboard", status_code=302)
    else:
        # Si no está autenticado, ir al login
        return RedirectResponse(url="/ui/login", status_code=302)

# Página de dashboard simple
@app.get("/ui/dashboard")
async def dashboard(request: Request):
    """Dashboard principal"""
    if not is_authenticated(request):
        return RedirectResponse(url="/ui/login", status_code=302)
    
    # Templates básico para el dashboard
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Dashboard",
            "user": {"username": "admin", "is_admin": True}  # Mock user data
        }
    )

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear directorios si no existen
UPLOAD_DIR = "uploads"
PLAYLIST_DIR = "playlists"
STATIC_DIR = "static"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PLAYLIST_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/playlists", StaticFiles(directory=PLAYLIST_DIR), name="playlists")

templates = Jinja2Templates(directory='templates')

# Incluir routers en orden
app.include_router(ui_auth_router)      # /ui/login, /ui/register, etc.
app.include_router(auth_router)         # Rutas de autenticación API originales
app.include_router(users_router)        # Gestión de usuarios original
app.include_router(videos.router)
app.include_router(playlists.router)
app.include_router(raspberry.router)
app.include_router(ui.router)
app.include_router(devices.router)
app.include_router(device_playlists.router)
app.include_router(services.router)
app.include_router(device_service_api.router)
app.include_router(playlist_checker_router)

# Middleware de autenticación corregido que reconoce cookies
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Middleware de autenticación que maneja cookies de sesión
    """
    path = request.url.path
    
    # Rutas públicas que no requieren autenticación
    public_paths = [
        "/login",
        "/ui/login", 
        "/ui/register",
        "/ui/logout",
        "/static/", 
        "/docs", 
        "/redoc", 
        "/openapi.json",
        "/api/devices",
        "/api/raspberry/"
    ]
    
    # Si es una ruta pública, continuar
    if any(path.startswith(public_path) for public_path in public_paths):
        response = await call_next(request)
        return response
    
    # Para rutas protegidas de UI, verificar autenticación por cookie O token
    if path.startswith("/ui/"):
        # Verificar cookie de sesión primero
        if is_authenticated(request):
            response = await call_next(request)
            return response
        
        # Si no hay cookie, verificar header Authorization
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            response = await call_next(request)
            return response
        
        # Sin autenticación, redireccionar a login
        login_url = "/ui/login"
        return RedirectResponse(url=login_url, status_code=302)
    
    # Para rutas API, verificar token o cookie
    elif path.startswith("/api/") and not any(path.startswith(p) for p in ["/api/devices", "/api/raspberry/"]):
        # Verificar cookie primero
        if is_authenticated(request):
            response = await call_next(request)
            return response
            
        # Verificar header Authorization
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            response = await call_next(request)
            return response
        
        # Sin autenticación para API, devolver 401
        return JSONResponse(
            content={"detail": "Token de acceso requerido"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Continuar con la solicitud
    response = await call_next(request)
    return response

# Evento de inicio
@app.on_event("startup")
async def startup_event():
    logger.info("Aplicación iniciada correctamente")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)