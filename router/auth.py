# router/auth.py
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import os

from models.database import get_db
from models import models
from utils.auth import (
    authenticate_user, 
    create_access_token, 
    get_current_active_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Create the auth router
router = APIRouter(tags=["auth"])

# Set up templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Login page route
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: Optional[str] = None):
    """Return the login page HTML"""
    # Check if user is already logged in
    if request.session.get("access_token"):
        # If next parameter exists, redirect there, otherwise to homepage
        if next:
            return RedirectResponse(url=next, status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(url="/ui/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Render login page
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login", "next": next}
    )

# Login API endpoint
@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Handle login form submission"""
    # Authenticate user
    user = authenticate_user(db, username, password)
    if not user:
        # If authentication fails, redirect back to login with error
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Login",
                "error": "Invalid username or password",
                "username": username,
                "next": next
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Create access token for the user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # Update last login timestamp
    user.last_login = datetime.now()
    db.commit()
    
    # Store token in session
    request.session["access_token"] = access_token
    request.session["username"] = user.username
    request.session["is_admin"] = user.is_admin
    
    # Redirect to requested next page or home
    redirect_url = next if next else "/ui/"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

# Logout route
@router.get("/logout")
async def logout(request: Request):
    """Log the user out by clearing the session"""
    # Clear session
    request.session.clear()
    # Redirect to login page
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

# API token endpoint for OAuth2
@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Handle API token requests using OAuth2"""
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # Update last login timestamp
    user.last_login = datetime.now()
    db.commit()
    
    # Return token
    return {"access_token": access_token, "token_type": "bearer"}

# User registration (administrative function)
@router.post("/users")
async def create_user(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    is_admin: bool = Form(False),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new user (requires admin privileges)"""
    # Check if current user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create users"
        )
    
    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(models.User).filter(models.User.email == email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = models.User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_admin=is_admin
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"username": db_user.username, "email": db_user.email, "success": True}

# Initial setup route to create the first admin user
@router.post("/setup/init")
async def initialize_admin(
    request: Request,
    setup_key: str = Form(...),
    admin_username: str = Form(...),
    admin_password: str = Form(...),
    admin_email: str = Form(...),
    admin_full_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """Initialize the first admin user - only works if there are no users in the database"""
    # Check setup key (should be set as an environment variable in production)
    expected_key = os.environ.get("SETUP_KEY", "defaultsetupkey")
    if setup_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid setup key"
        )
    
    # Check if any users already exist
    user_count = db.query(models.User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup has already been completed. Users exist in the database."
        )
    
    # Create the admin user
    admin_user = models.User(
        username=admin_username,
        email=admin_email,
        full_name=admin_full_name,
        hashed_password=get_password_hash(admin_password),
        is_admin=True
    )
    
    db.add(admin_user)
    db.commit()
    
    return {"success": True, "message": "Admin user created successfully"}