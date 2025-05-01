# init_db.py
# Script para inicializar la base de datos y crear el usuario administrador inicial

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Añadir el directorio raíz al path
sys.path.append(str(Path(__file__).resolve().parent))

# Cargar variables de entorno
load_dotenv()

from models.database import SessionLocal, engine
from models.models import Base, User

def init_db():
    """
    Inicializa la base de datos y crea un usuario administrador si no existe ninguno
    """
    print("Inicializando base de datos...")
    
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente")
    
    # Crear sesión
    db = SessionLocal()
    
    try:
        # Verificar si ya existe algún usuario
        user_count = db.query(User).count()
        
        if user_count == 0:
            # Obtener credenciales del archivo .env o usar valores por defecto
            admin_username = os.getenv("AUTH_USERNAME", "admin")
            admin_password = os.getenv("AUTH_PASSWORD", "admin123")
            admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
            
            # Crear el usuario administrador
            admin = User(
                username=admin_username,
                email=admin_email,
                fullname="Administrador",
                is_admin=True,
                is_active=True
            )
            
            # Establecer la contraseña de forma segura
            admin.password = admin_password
            
            # Guardar el usuario
            db.add(admin)
            db.commit()
            print(f"Usuario administrador '{admin_username}' creado correctamente")
            print(f"Email: {admin_email}")
            print(f"Contraseña: {admin_password}")
            print("\n¡IMPORTANTE! Cambie esta contraseña después del primer inicio de sesión")
        else:
            print(f"Ya existen {user_count} usuarios en la base de datos")
            
    except Exception as e:
        print(f"Error al inicializar la base de datos: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("Proceso completado")