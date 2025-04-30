# router/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from models.database import get_db
from models import models
from utils.auth import get_current_active_user, get_password_hash

router = APIRouter(
    prefix="/ui/users",
    tags=["users"]
)

@router.post("/")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Create a new user (requires admin privileges)"""
    # Check if current user is admin
    if not request.session.get("is_admin", False):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"success": False, "detail": "Only administrators can create users"}
        )
    
    # Check if username already exists
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "detail": "Username already registered"}
        )
    
    # Check if email already exists
    existing_email = db.query(models.User).filter(models.User.email == email).first()
    if existing_email:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "detail": "Email already registered"}
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
    
    return {"success": True, "username": db_user.username, "email": db_user.email}

@router.post("/edit")
async def edit_user(
    request: Request,
    user_id: int = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: Optional[str] = Form(None),
    is_admin: bool = Form(False),
    disabled: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Update user information (requires admin privileges)"""
    # Check if current user is admin
    if not request.session.get("is_admin", False):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"success": False, "detail": "Only administrators can edit users"}
        )
    
    # Get the user to update
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "detail": "User not found"}
        )
    
    # Check if email exists for another user
    existing_email = db.query(models.User).filter(
        models.User.email == email,
        models.User.id != user_id
    ).first()
    if existing_email:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "detail": "Email already used by another user"}
        )
    
    # Update user fields
    user.email = email
    user.full_name = full_name
    user.is_admin = is_admin
    user.disabled = disabled
    
    # Update password if provided
    if password:
        user.hashed_password = get_password_hash(password)
    
    db.commit()
    
    return {"success": True, "username": user.username}

@router.post("/delete")
async def delete_user(
    request: Request,
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Delete a user (requires admin privileges)"""
    # Check if current user is admin
    if not request.session.get("is_admin", False):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"success": False, "detail": "Only administrators can delete users"}
        )
    
    # Get the user to delete
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "detail": "User not found"}
        )
    
    # Prevent deleting the current logged in user
    current_username = request.session.get("username")
    if user.username == current_username:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "detail": "You cannot delete your own account"}
        )
    
    # Delete the user
    db.delete(user)
    db.commit()
    
    return {"success": True}