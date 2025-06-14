# create_admin.py - Script para crear usuario administrador

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.models import User, Base
from models.database import SQLALCHEMY_DATABASE_URL

def create_admin_user():
    """Crear usuario administrador por defecto"""
    
    # Crear engine y sesión
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Verificar si ya existe un administrador
        admin_exists = db.query(User).filter(User.is_admin == True).first()
        
        if admin_exists:
            print(f"✓ Ya existe un usuario administrador: {admin_exists.username}")
            return admin_exists
        
        # Verificar si existe el usuario 'admin'
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if existing_admin:
            # Actualizar permisos de admin si existe pero no es admin
            existing_admin.is_admin = True
            existing_admin.is_active = True
            db.commit()
            print(f"✓ Usuario 'admin' actualizado con permisos de administrador")
            return existing_admin
        
        # Crear nuevo usuario administrador
        print("Creando usuario administrador por defecto...")
        
        admin_user = User(
            username="admin",
            email="admin@localhost",
            fullname="Administrador del Sistema",
            is_admin=True,
            is_active=True
        )
        
        # Establecer contraseña
        admin_user.password = "Ikea,.2010"  # Esto usará el setter que hashea la contraseña
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✓ Usuario administrador creado exitosamente")
        print(f"  Usuario: {admin_user.username}")
        print(f"  Email: {admin_user.email}")
        print(f"  Contraseña")
        print("\n⚠️  IMPORTANTE: Cambiar la contraseña por defecto después del primer login")
        
        return admin_user
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creando usuario administrador: {str(e)}")
        return None
    finally:
        db.close()

def verify_user_model():
    """Verificar que el modelo User funcione correctamente"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Intentar consultar usuarios
        users_count = db.query(User).count()
        print(f"✓ Modelo User funcional. Usuarios en BD: {users_count}")
        return True
    except Exception as e:
        print(f"✗ Error con modelo User: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Creación de Usuario Administrador ===")
    
    # Verificar modelo
    if not verify_user_model():
        print("Error: Modelo User no funcional")
        sys.exit(1)
    
    # Crear administrador
    admin = create_admin_user()
    
    if admin:
        print("\n=== Login Credentials ===")
        print("URL: http://localhost:8000/ui/login")
        print("Usuario: admin")
        print("Contraseña")
        print("\n=== Next Steps ===")
        print("1. Iniciar servidor: uvicorn main:app --reload")
        print("2. Hacer login con las credenciales arriba")
        print("3. Cambiar contraseña por defecto")
        print("4. Crear otros usuarios según necesidad")
    else:
        print("Error: No se pudo crear usuario administrador")
        sys.exit(1)