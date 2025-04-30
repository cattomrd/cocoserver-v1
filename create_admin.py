#!/usr/bin/env python3
# create_admin.py - Script to create an admin user from the command line

import os
import sys
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import models and utilities
from models.database import SessionLocal
from models.models import User
from utils.auth import get_password_hash

def create_admin_user(username, password, email, full_name, force=False):
    """
    Create an admin user in the database
    
    Args:
        username (str): Admin username
        password (str): Admin password
        email (str): Admin email
        full_name (str): Admin full name
        force (bool): Force creation even if users already exist
    
    Returns:
        bool: Success status
    """
    db = SessionLocal()
    try:
        # Check if any users already exist
        user_count = db.query(User).count()
        if user_count > 0 and not force:
            print("Users already exist in the database. Use --force to override.")
            return False
        
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"Username '{username}' already exists.")
            return False
        
        # Check if email already exists
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            print(f"Email '{email}' already registered.")
            return False
        
        # Create the admin user
        admin_user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print(f"Admin user '{username}' created successfully.")
        return True
    
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {str(e)}")
        return False
    
    finally:
        db.close()

def main():
    """Command line interface for creating an admin user"""
    parser = argparse.ArgumentParser(description="Create an admin user for the Raspberry Pi Registry")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--full-name", required=True, help="Admin full name")
    parser.add_argument("--force", action="store_true", help="Force creation even if users already exist")
    
    args = parser.parse_args()
    
    success = create_admin_user(
        args.username,
        args.password,
        args.email,
        args.full_name,
        args.force
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()