# utils/auth.py
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Callable, Dict, Any
import secrets
import base64
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv

from models.database import get_db
from models.models import User

# Load environment variables
load_dotenv()

# Store sessions - in production, you would use a proper session store like Redis
# Format: {session_id: {'user_id': user_id, 'username': username, 'is_admin': bool, 'expires': expires_datetime}}
sessions = {}

# Get session configuration from environment variables
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "default-secret-key-change-this")
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

# Used for initial setup if no users exist
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")

def create_session(user_id: int, username: str, is_admin: bool) -> str:
    """Create a new session for the user and return the session ID"""
    session_id = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
    sessions[session_id] = {
        'user_id': user_id,
        'username': username,
        'is_admin': is_admin,
        'expires': expires
    }
    return session_id

def validate_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Validate session ID and return user info if valid, None otherwise"""
    if not session_id or session_id not in sessions:
        return None
    
    session = sessions[session_id]
    # Check if session has expired
    if session['expires'] < datetime.now():
        del sessions[session_id]
        return None
        
    return {
        'user_id': session['user_id'],
        'username': session['username'],
        'is_admin': session['is_admin']
    }

async def admin_required(request: Request):
    """
    Dependency to check if the user is an admin
    """
    session_id = request.cookies.get("session")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user_info = validate_session(session_id)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )
    
    if not user_info.get('is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return user_info

def get_current_user(request: Request):
    """
    Extract current user information from session
    Returns None if not authenticated
    """
    session_id = request.cookies.get("session")
    if not session_id:
        return None
    
    return validate_session(session_id)

def auth_middleware(
    public_paths: List[str] = ["/login", 
                            "/static/", 
                            "/api/raspberry/", 
                            "/api/devices"],
    admin_paths: List[str] = ["/ui/users/",
                            "/docs", 
                            "/redoc", 
                            "/openapi.json", ],
    api_token_enabled: bool = True
):
    """
    Middleware to check authentication for protected routes
    
    Arguments:
        public_paths: List of path prefixes that don't require authentication
        admin_paths: List of path prefixes that require admin privileges
        api_token_enabled: Whether to allow API token authentication for API routes
    """
    async def authenticate(request: Request, call_next):
        # Check if the path is public
        path = request.url.path
        if any(path.startswith(p) for p in public_paths):
            return await call_next(request)
        
        # Check for API routes and API token authentication
        if api_token_enabled and path.startswith("/api/"):
            # Check for API token in headers
            api_token = request.headers.get("Authorization")
            if api_token and api_token.startswith("Bearer "):
                token = api_token.replace("Bearer ", "")
                # In a real app, validate the token against a database
                # For now, using a simple check
                if token == SECRET_KEY:
                    return await call_next(request)
        
        # Check for session cookie
        session_id = request.cookies.get("session")
        user_info = validate_session(session_id)
        
        if not user_info:
            # For API routes, return 401 Unauthorized
            if path.startswith("/api/"):
                return JSONResponse(
                    content={"detail": "Invalid or expired authentication"},
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            # For UI routes, redirect to login page
            # Add the original requested URL as the "next" parameter
            return RedirectResponse(
                url=f"/login?next={request.url.path}", 
                status_code=status.HTTP_302_FOUND
            )
        
        # Check for admin-only paths
        if any(path.startswith(p) for p in admin_paths) and not user_info.get('is_admin', False):
            # For API routes, return 403 Forbidden
            if path.startswith("/api/"):
                return JSONResponse(
                    content={"detail": "Admin privileges required"},
                    status_code=status.HTTP_403_FORBIDDEN
                )
                
            # For UI routes, redirect to access denied page
            return RedirectResponse(
                url="/access-denied", 
                status_code=status.HTTP_302_FOUND
            )
            
        # Add user info to request state
        request.state.user = user_info
        
        # User is authenticated and authorized, proceed with request
        return await call_next(request)
    
    return authenticate

async def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with username and password
    Creates the default admin user if no users exist
    """
    # Check if we need to create the default admin user
    user_count = db.query(User).count()
    if user_count == 0:
        # Create default admin user
        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            fullname="Default Administrator",
            is_admin=True
        )
        admin.password = DEFAULT_ADMIN_PASSWORD
        db.add(admin)
        db.commit()
        db.refresh(admin)
    
    # Now try to authenticate
    return User.authenticate(db, username, password)