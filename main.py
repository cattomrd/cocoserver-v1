# Actualizar main.py

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import logging
load_dotenv()

import os
import uvicorn
# Importar los modelos para crear las tablas
from models import models

from models.database import engine

# Importar los routers
from router import videos, playlists, raspberry, ui, services, devices, device_playlists

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

ssh_user = os.environ.get('SSH_USER')
ssh_password = os.environ.get('SSH_PASS')
print(ssh_user, ssh_password)
# Verificar si las variables críticas están definidas

if not ssh_user:
    logger.warning("La variable SSH_USER no está definida en el archivo .env")
if not ssh_password:
    logger.warning("La variable SSH_PASSWORD no está definida en el archivo .env")

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

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')

# Montar los directorios estáticos
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/playlists", StaticFiles(directory=PLAYLIST_DIR), name="playlists")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Incluir los routers
app.include_router(videos.router)
app.include_router(playlists.router)
app.include_router(raspberry.router)
app.include_router(ui.router)
app.include_router(services.router)
app.include_router(devices.router)  # Router de dispositivos
app.include_router(device_playlists.router)  # Nuevo router

# Ruta raíz
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request):
    # Redireccionar al dashboard UI
    return templates.TemplateResponse("index.html", {"request": request, "title": "Raspberry Pi Registry"})

# Ejecutar la aplicación con uvicorn (para desarrollo)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)