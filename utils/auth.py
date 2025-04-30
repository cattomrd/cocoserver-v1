# utils/auth.py
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel
import bcrypt
import os
import logging
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware


from models.database import get_db
from models import models

# Configure logging
logger = logging.getLogger(__name__)

# Secret key for JWT token, should be set from environment variable in production
SECRET_KEY = os.environ.get("SECRET_KEY", "insecuresecretinsecuresecretinsecuresecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Define models for user credentials and token
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

# OAuth2 Bearer token for API authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Function to create a password hash
def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash from a password string"""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    return hashed_password.decode()

# Function to verify a password against the stored hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

# Function to authenticate a user
def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticate a user by checking username and password"""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# Function to create an access token
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token with an optional expiration time"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to get the current user from the token
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """Get the current user from the JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if token is None:
            raise credentials_exception
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

# Function to get the current active user
async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Check if the current user is active"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Check if the user is authenticated for web routes
async def is_authenticated(request: Request) -> bool:
    """Check if the user is authenticated by looking for a valid access token in the session"""
    try:
        # Attempt to get token from session - handle case where session might not exist
        token = getattr(request, "session", {}).get("access_token")
        if not token:
            return False
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return False
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp is None or datetime.utcnow() > datetime.fromtimestamp(exp):
                return False
            
            return True
        except JWTError:
            return False
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return False

# Middleware to protect routes that require authentication
async def auth_middleware(request: Request, db: Session = Depends(get_db)) -> None:
    """Middleware to protect routes that require authentication"""
    try:
        # Skip authentication for login, logout, setup, and static routes
        path = request.url.path
        if (path.startswith("/login") or 
            path.startswith("/static") or 
            path.startswith("/setup") or 
            path.startswith("/ui") or
            path.startswith("/ui/devices") or
            path.startswith("/api/videos") or
            path.startswith("/ui/users") or
            path.startswith("/docs") or
            path == "/"):
            return None
        
        # List of API routes that don't require authentication (public API endpoints)
        public_api_routes = [
            "/api/raspberry/playlists/active/{device_id}",  # Make the active playlists API accessible to Raspberry Pi devices
            "/api/videos",  # Allow access to videos for Raspberry Pi clients
        ]
        
        # Check if the path starts with any of the public API routes
        for route in public_api_routes:
            if path.startswith(route):
                return None
        
        # Check if user is authenticated
        authenticated = await is_authenticated(request)
        if not authenticated and not path.startswith("/api"):
            # Redirect to login page for web routes
            return RedirectResponse(url="/login?next=" + request.url.path, status_code=status.HTTP_303_SEE_OTHER)
        elif not authenticated and path.startswith("/api"):
            # Return 401 for API routes that aren't in public_api_routes
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return None
    except Exception as e:
        logger.error(f"Auth middleware error: {str(e)}")
        # For safety, if there's an error in the auth middleware, 
        # treat non-API routes as unauthenticated and API routes as unauthorized
        if not path.startswith("/api"):
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication error",
                headers={"WWW-Authenticate": "Bearer"},
            )