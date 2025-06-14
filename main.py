# main.py - Versión corregida

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

# IMPORTANTE: Rutas de redirección ANTES de cualquier middleware
@app.get("/login")
async def redirect_login():
    """Redireccionar /login a /ui/login"""
    return RedirectResponse(url="/ui/login", status_code=301)

@app.get("/")
async def redirect_root():
    """Redireccionar / a /ui/login"""
    return RedirectResponse(url="/ui/login", status_code=302)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a los orígenes permitidos
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

# Incluir routers
app.include_router(ui_auth_router)      # /ui/login, /ui/register, etc.
app.include_router(auth_router)         # Rutas de autenticación API
app.include_router(users_router)        # Gestión de usuarios
app.include_router(videos.router)
app.include_router(playlists.router)
app.include_router(raspberry.router)
app.include_router(ui.router)
app.include_router(devices.router)
app.include_router(device_playlists.router)
app.include_router(services.router)
app.include_router(device_service_api.router)
app.include_router(playlist_checker_router)

# Middleware de autenticación simple y corregido
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Middleware de autenticación corregido
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
    
    # Verificar si es una ruta pública
    is_public = any(path.startswith(public_path) for public_path in public_paths)
    
    if is_public:
        # Para rutas públicas, continuar normalmente
        response = await call_next(request)
        return response
    
    # Para rutas protegidas de UI, verificar autenticación básica
    if path.startswith("/ui/"):
        auth_header = request.headers.get("Authorization")
        
        # Si no hay token de autorización, redireccionar a login
        if not auth_header or not auth_header.startswith("Bearer "):
            next_url = str(request.url)
            login_url = f"/ui/login?next={next_url}"
            return RedirectResponse(url=login_url, status_code=302)
    
    # Para rutas API protegidas, verificar token
    elif path.startswith("/api/") and not any(path.startswith(p) for p in ["/api/devices", "/api/raspberry/"]):
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
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
    
    # Iniciar servicios en background si están disponibles
    try:
        from utils.ping_checker import start_background_ping_checker
        start_background_ping_checker(app)
        logger.info("Verificador de ping iniciado")
    except ImportError:
        logger.warning("Verificador de ping no disponible")
    
    try:
        from utils.list_checker import start_playlist_checker
        start_playlist_checker(app, check_interval=300)
        logger.info("Verificador de listas de reproducción iniciado")
    except ImportError:
        logger.warning("Verificador de listas no disponible")

# Evento de cierre
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Cerrando aplicación...")

# Ejecutar la aplicación
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)