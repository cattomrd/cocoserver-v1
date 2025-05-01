# router/auth.py
from fastapi import APIRouter, Request, Response, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
from sqlalchemy.orm import Session

from models.database import get_db
from utils.auth import authenticate_user, create_session, get_current_user

# Setup logging
logger = logging.getLogger(__name__)

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["authentication"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/"):
    """
    Render the login page
    """
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request, 
            "title": "Login", 
            "next": next
        }
    )

@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db)):
    """
    Handle login form submission
    """
    # Validate credentials
    user = await authenticate_user(db, username, password)
    
    if user:
        # Create session
        session_id = create_session(user.id, user.username, user.is_admin)
        
        # Set cookie
        response = RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="session",
            value=session_id,
            httponly=True,
            max_age=86400,  # 24 hours
            path="/"
        )
        
        logger.info(f"User {username} logged in successfully")
        return response
    else:
        logger.warning(f"Failed login attempt for user {username}")
        # Show error message
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Login",
                "error": "Usuario o contraseña inválidos",
                "username": username,  # Return username for convenience
                "next": next
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )

@router.get("/logout")
async def logout(request: Request, response: Response):
    """
    Handle logout - clear session cookie
    """
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="session")
    return response

@router.get("/access-denied", response_class=HTMLResponse)
async def access_denied(request: Request):
    """
    Access denied page
    """
    user_info = get_current_user(request)
    return templates.TemplateResponse(
        "access_denied.html", 
        {
            "request": request, 
            "title": "Acceso Denegado",
            "user": user_info
        }
    )

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """
    User profile page - example of a protected route
    """
    user_info = get_current_user(request)
    if not user_info:
        return RedirectResponse(url="/login?next=/profile", status_code=status.HTTP_302_FOUND)
        
    return templates.TemplateResponse(
        "profile.html", 
        {
            "request": request,
            "title": "Mi Perfil",
            "user": user_info
        }
    )