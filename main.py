# main.py with authentication integration
# Updated to include authentication middleware and routes

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from dotenv import load_dotenv
import logging
import os
import uvicorn

# Load environment variables
load_dotenv()

# Import the models for creating tables
from models import models
from models.database import engine

# Import the routers
from router import device_service_api, auth, users, device_playlists, devices, playlists, raspberry, services_enhanced as services, ui, users, videos

# Import authentication middleware
from utils.auth import auth_middleware

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Send logs to console
    ]
)
logger = logging.getLogger(__name__)

# Create the FastAPI application
app = FastAPI(
    title="API de Gestión de Videos",
    description="API para gestionar videos y listas de reproducción para Raspberry Pi",
    version="1.0.0"
)

# Add session middleware (for web authentication)
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.environ.get("SECRET_KEY")
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, limit to allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
UPLOAD_DIR = "uploads"
PLAYLIST_DIR = "playlists"
STATIC_DIR = "static"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PLAYLIST_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static directories
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/playlists", StaticFiles(directory=PLAYLIST_DIR), name="playlists")


# app.add_middleware(HTTPSRedirectMiddleware)  # Redirige HTTP → HTTPS
# app.add_middleware(SessionMiddleware, ...)  # Luego agrega el middleware de sesión
# Include routers
app.include_router(devices.router)
app.include_router(device_playlists.router)
app.include_router(device_service_api.router)
app.include_router(auth.router)  # Add the authentication router
app.include_router(users.router)  # Add the users management router
app.include_router(raspberry.router)
app.include_router(playlists.router)
app.include_router(services.router)
app.include_router(ui.router)
app.include_router(videos.router)



# Set up templates
templates = Jinja2Templates(directory="templates")

# Add authentication middleware
@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    """Middleware to check authentication for all routes"""
    # Check authentication
    result = await auth_middleware(request)
    if result is not None:
        return result
    
    # Proceed with the request if authenticated
    response = await call_next(request)
    return response

# Root route - redirect to UI or login
@app.get("/")
async def root(request: Request):
    """Root route redirects to UI dashboard if logged in, otherwise to login page"""
    # Check if user is logged in
    if request.session.get("access_token"):
        return RedirectResponse(url="/ui/", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

# Setup route for initial configuration
@app.get("/setup")
async def setup_page(request: Request):
    """Initial setup page to create the first admin user"""
    from models.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Check if any users already exist
        user_count = db.query(models.User).count()
        if user_count > 0:
            # Setup already completed, redirect to login
            return RedirectResponse(url="/login", status_code=303)
        
        # Render setup page
        return templates.TemplateResponse(
            "setup.html",
            {"request": request, "success": False}
        )
    finally:
        db.close()

# Execute the application with uvicorn (for development)
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)