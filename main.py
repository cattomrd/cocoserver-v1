# Updated main.py con el verificador de listas

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import logging
from utils.ping_checker import start_background_ping_checker
from utils.list_checker import start_playlist_checker  # Nueva importación

load_dotenv()

import os
import uvicorn
# Importar los modelos para crear las tablas
from models import models

from models.database import engine

# Importar los routers
from router import videos, playlists, raspberry, ui, devices, device_playlists, services_enhanced as services, device_service_api
from router.auth_enhanced import router as auth_router
from router.users_enhanced import router as users_router
from router.playlist_checker_api import router as playlist_checker_router


# Import the authentication middleware
from utils.auth import auth_middleware

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Enviar logs a la consola
    ]
)
logger = logging.getLogger(__name__)

# Crear la aplicación FastAPI
app = FastAPI(
    title="API de Gestión de Videos",
    description="API para gestionar videos y listas de reproducción para Raspberry Pi",
    version="1.0.0"
)

# Iniciar verificadores en background
start_background_ping_checker(app)
start_playlist_checker(app, check_interval=300)  # Verificar cada 5 minutos

# Add the authentication middleware with admin paths
app.middleware("http")(
    auth_middleware(
        public_paths=[
            "/login", 
            "/static/", 
            "/api/devices",  # Allow device registration
            "/api/raspberry/",
            "/api/videos/" 
        ],
        admin_paths=[
            "/ui/users/",  # Only admins can access user management
        ]
    )
)

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
templates = Jinja2Templates(directory='templates')

# Montar los directorios estáticos
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/playlists", StaticFiles(directory=PLAYLIST_DIR), name="playlists")

# Include the authentication router
app.include_router(auth_router)

# Include user management router
app.include_router(users_router)

# Incluir los routers
app.include_router(videos.router)
app.include_router(playlists.router)
app.include_router(raspberry.router)
app.include_router(ui.router)
app.include_router(services.router)
app.include_router(devices.router)  # Router de dispositivos
app.include_router(device_playlists.router)  # Nuevo router
app.include_router(device_service_api.router)  # Router para la API de servicios de dispositivos
app.include_router(playlist_checker_router)  # Router para verificación de listas de servicios de dispositivos

# Añadir middleware para proporcionar información del usuario a las plantillas
@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    # La información del usuario ya está en request.state.user gracias al middleware de autenticación
    response = await call_next(request)
    return response

# Ruta raíz
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request):
    # Redireccionar al dashboard UI
    return templates.TemplateResponse("index.html", {"request": request, "title": "Raspberry Pi Registry"})

# Evento de inicio para configuraciones adicionales
@app.on_event("startup")
async def startup_event():
    logger.info("Aplicación iniciada correctamente")
    logger.info("Verificador de ping iniciado")
    logger.info("Verificador de listas de reproducción iniciado")

# Evento de cierre
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Cerrando aplicación...")

# Ejecutar la aplicación con uvicorn (para desarrollo)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)