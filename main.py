from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os
import uvicorn
# Importar los modelos para crear las tablas
from models import models
from models.database import engine

# Importar los routers
from router import videos, playlists, raspberry, ui, services, devices

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
#os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')

# Montar los directorios estáticos
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/playlists", StaticFiles(directory=PLAYLIST_DIR), name="playlists")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Incluir los routers
app.include_router(videos.router, prefix="/api")
app.include_router(playlists.router, prefix="/api")
app.include_router(raspberry.router, prefix="/api")
app.include_router(ui.router)
app.include_router(services.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
# Ruta raíz
templates = Jinja2Templates(directory="templates")

# Montar directorios estáticos

# Ruta para /templates/index.html usando Jinja2Templates
# @app.get("/templates/index.html")
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

@app.get("/")
async def root(request: Request):
    # Redireccionar al dashboard UI
    return templates.TemplateResponse("index.html", {"request": request, "title": "Raspberry Pi Registry"})


# Ejecutar la aplicación con uvicorn (para desarrollo)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)