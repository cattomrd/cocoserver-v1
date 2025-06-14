# migrations/add_ad_support.py - Script para migrar la base de datos

from sqlalchemy import text
from models.database import engine
import logging

logger = logging.getLogger(__name__)

def apply_migration():
    """Aplica las migraciones para soporte de Active Directory"""
    
    migration_script = """
    -- Agregar nuevas columnas a la tabla users
    ALTER TABLE users ADD COLUMN department TEXT;
    ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local';
    ALTER TABLE users ADD COLUMN ad_dn TEXT;
    ALTER TABLE users ADD COLUMN last_ad_sync DATETIME;
    ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;
    
    -- Hacer password_hash nullable para usuarios de AD
    -- Nota: En SQLite no se puede modificar columnas directamente
    -- Se necesita recrear la tabla
    
    -- Crear nueva tabla users con la estructura actualizada
    CREATE TABLE users_new (
        id INTEGER PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE,
        password_hash VARCHAR(128),
        fullname VARCHAR(100),
        department VARCHAR(100),
        is_active BOOLEAN DEFAULT 1,
        is_admin BOOLEAN DEFAULT 0,
        auth_provider VARCHAR(20) DEFAULT 'local',
        ad_dn VARCHAR(500),
        last_ad_sync DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME
    );
    
    -- Copiar datos existentes
    INSERT INTO users_new (
        id, username, email, password_hash, fullname, is_active, 
        is_admin, created_at, last_login
    )
    SELECT 
        id, username, email, password_hash, fullname, is_active, 
        is_admin, created_at, last_login
    FROM users;
    
    -- Eliminar tabla antigua y renombrar nueva
    DROP TABLE users;
    ALTER TABLE users_new RENAME TO users;
    
    -- Crear índices
    CREATE INDEX idx_users_username ON users(username);
    CREATE INDEX idx_users_email ON users(email);
    CREATE INDEX idx_users_auth_provider ON users(auth_provider);
    CREATE INDEX idx_users_is_active ON users(is_active);
    CREATE INDEX idx_users_is_admin ON users(is_admin);
    
    -- Crear tabla de logs de sincronización AD
    CREATE TABLE ad_sync_logs (
        id INTEGER PRIMARY KEY,
        sync_type VARCHAR(50) NOT NULL,
        status VARCHAR(20) NOT NULL,
        message TEXT,
        users_processed INTEGER DEFAULT 0,
        users_created INTEGER DEFAULT 0,
        users_updated INTEGER DEFAULT 0,
        users_errors INTEGER DEFAULT 0,
        duration_seconds REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_ad_sync_logs_created_at ON ad_sync_logs(created_at);
    CREATE INDEX idx_ad_sync_logs_status ON ad_sync_logs(status);
    """
    
    try:
        # Verificar si ya se aplicó la migración
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result]
            
            if 'auth_provider' in columns:
                print("Migración ya aplicada anteriormente.")
                return True
        
        print("Aplicando migración para soporte de Active Directory...")
        
        # Ejecutar la migración
        with engine.begin() as conn:
            for statement in migration_script.split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))
        
        print("Migración aplicada correctamente.")
        return True
        
    except Exception as e:
        logger.error(f"Error aplicando migración: {str(e)}")
        print(f"Error aplicando migración: {str(e)}")
        return False

def create_default_admin():
    """Crea un usuario administrador por defecto"""
    from sqlalchemy.orm import sessionmaker
    from models.models import User, AuthProvider
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Verificar si ya existe un administrador
        admin_user = session.query(User).filter(User.is_admin == True).first()
        
        if admin_user:
            print(f"Usuario administrador ya existe: {admin_user.username}")
            return True
        
        # Crear usuario administrador por defecto
        default_admin = User.create_user(
            db=session,
            username="admin",
            email="admin@localhost",
            password="admin123",  # Cambiar en producción
            fullname="Administrador del Sistema",
            is_admin=True,
            auth_provider=AuthProvider.LOCAL.value
        )
        
        print(f"Usuario administrador creado: {default_admin.username}")
        print("IMPORTANTE: Cambiar la contraseña por defecto (admin123)")
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error creando administrador por defecto: {str(e)}")
        print(f"Error creando administrador por defecto: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    """Ejecutar migración directamente"""
    print("=== Migración para soporte de Active Directory ===")
    
    # Aplicar migración
    if apply_migration():
        print("✓ Migración de base de datos completada")
        
        # Crear administrador por defecto si no existe
        if create_default_admin():
            print("✓ Usuario administrador verificado/creado")
        else:
            print("✗ Error creando usuario administrador")
    else:
        print("✗ Error en migración de base de datos")
    
    print("\n=== Próximos pasos ===")
    print("1. Configurar variables de Active Directory en .env")
    print("2. Instalar dependencias: pip install ldap3 python-ldap")
    print("3. Cambiar contraseña del administrador por defecto")
    print("4. Configurar cuenta de servicio en Active Directory")
    print("5. Probar conexión con AD desde la interfaz web")