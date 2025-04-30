# Actualización de main.py para incluir autenticación JWT

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import logging
import os
import uvicorn

# Importar los modelos para crear las tablas
from models import models
from models.database import engine

# Importar los routers
from router import videos, playlists, raspberry, ui, services_enhanced as services, devices, device_playlists, auth,ui_auth, device_service_api

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Enviar logs a la consola
    ]
)
logger = logging.getLogger(__name__)

# Verificar SECRET_KEY en las variables de entorno
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    logger.warning("JWT_SECRET_KEY no está definida en variables de entorno. Se usará una clave predeterminada.")
    logger.warning("Para producción, se recomienda definir una clave secreta fuerte en .env")

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

# Crear la aplicación FastAPI
app = FastAPI(
    title="API de Gestión de Videos",
    description="API para gestionar videos y listas de reproducción para Raspberry Pi",
    version="1.0.0"
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

# Montar los directorios estáticos
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/playlists", StaticFiles(directory=PLAYLIST_DIR), name="playlists")


templates = Jinja2Templates(directory='templates')

# Incluir los routers
app.include_router(auth.router)  # Router de autenticación (debe ser el primero para priorizar las rutas)
app.include_router(ui_auth.router)  # Router para UI de autenticación
app.include_router(videos.router)
app.include_router(playlists.router)
app.include_router(raspberry.router)
app.include_router(ui.router)
app.include_router(services.router)
app.include_router(devices.router)
app.include_router(device_playlists.router)
app.include_router(device_service_api.router)

# Middleware para verificar la salud de la API
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # Permitir siempre las rutas de autenticación sin token
    if request.url.path in ["/api/auth/login", "/api/auth/token", "/api/auth/register"]:
        response = await call_next(request)
        return response
    
    # Para rutas de documentación y UI, permitir sin token
    if request.url.path.startswith(("/docs", "/redoc", "/openapi.json", "/ui/", "/static/")):
        response = await call_next(request)
        return response
    
    # Para las demás rutas, el control de autenticación lo harán las dependencias en cada endpoint
    response = await call_next(request)
    return response

# Ruta raíz
@app.get("/")
async def root(request: Request):
    # Redireccionar al dashboard UI
    return templates.TemplateResponse("login.html", {"request": request, "title": "Raspberry Pi Registry"})

# Crear usuario administrador por defecto si no existe
@app.on_event("startup")
async def create_default_admin():
    from sqlalchemy.orm import Session
    from models.database import SessionLocal
    import os
    
    # Obtener credenciales del administrador desde variables de entorno
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    admin_email = os.environ.get("ADMIN_EMAIL")
    
    db = SessionLocal()
    try:
        # Verificar si ya existe un administrador
        admin = db.query(models.User).filter(models.User.is_admin == True).first()
        if not admin:
            # Crear usuario administrador
            from models.models import User
            admin = User(
                username=admin_username,
                email=admin_email,
                full_name="Administrator",
                is_active=True,
                is_admin=True
            )
            admin.password = admin_password
            
            db.add(admin)
            db.commit()
            
            logger.info(f"Usuario administrador creado: {admin_username}")
        else:
            logger.info("Usuario administrador ya existe")
    except Exception as e:
        logger.error(f"Error al crear usuario administrador: {str(e)}")
    finally:
        db.close()

# Ejecutar la aplicación con uvicorn (para desarrollo)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)