#!/usr/bin/env python3
# create_admin.py - Script to create an admin user from the command line

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models and utilities after path setup
from models.database import SessionLocal
from models.models import User
from werkzeug.security import generate_password_hash

def create_admin_user(username, password, email, fullname, force=False):
    """
    Create an admin user in the database
    
    Args:
        username (str): Admin username
        password (str): Admin password
        email (str): Admin email
        fullname (str): Admin full name
        force (bool): Force creation even if users exist
    
    Returns:
        bool: True if successful, False otherwise
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
            fullname=fullname,
            password_hash=generate_password_hash(password),
            is_admin=True,
            is_active=True
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
    """
    Main function to handle command line arguments and create admin user
    """
    parser = argparse.ArgumentParser(description='Create an admin user')
    parser.add_argument('--username', help='Admin username')
    parser.add_argument('--password', help='Admin password')
    parser.add_argument('--email', help='Admin email')
    parser.add_argument('--fullname', help='Admin full name')
    parser.add_argument('--force', action='store_true', 
                    help='Force creation even if users exist')
    
    args = parser.parse_args()
    
    # Get values from command line arguments or environment variables
    username = args.username or os.environ.get('APP_USERNAME')
    password = args.password or os.environ.get('APP_PASSWORD')
    email = args.email or os.environ.get('APP_EMAIL')
    fullname = args.fullname or os.environ.get('APP_FULLNAME')
    
    # Validate required fields
    if not username:
        print("Error: Username is required (use --username or set APP_USERNAME)")
        sys.exit(1)
    
    if not password:
        print("Error: Password is required (use --password or set APP_PASSWORD)")
        sys.exit(1)
    
    if not email:
        print("Error: Email is required (use --email or set APP_EMAIL)")
        sys.exit(1)
    
    if not fullname:
        print("Error: Full name is required (use --fullname or set APP_FULLNAME)")
        sys.exit(1)
    
    # Create the admin user
    success = create_admin_user(username, password, email, fullname, args.force)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()