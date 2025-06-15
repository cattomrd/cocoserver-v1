#!/usr/bin/env python3
"""
Script de migración específico para PostgreSQL
Agrega soporte de Active Directory
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

user_db = os.environ.get('POSTGRES_USER')
password_db = os.environ.get('POSTGRES_PASSWORD')
db = os.environ.get('POSTGRES_DB')
server_db = os.environ.get('POSTGRES_HOST')

SQLALCHEMY_DATABASE_URL = f"postgresql://{user_db}:{password_db}@{server_db}/{db}"
def check_column_exists(conn, table_name, column_name):
    """Verifica si una columna existe en PostgreSQL"""
    try:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name})
        
        return result.fetchone() is not None
    except Exception:
        return False

def run_postgresql_migration():
    """Ejecuta la migración para PostgreSQL"""
    print("=== MIGRACIÓN POSTGRESQL PARA SOPORTE AD ===")
    
    # Obtener URL de base de datos
    database_url = f"postgresql://{user_db}:{password_db}@{server_db}/{db}"
    if not database_url:
        print("❌ DATABASE_URL no configurada")
        return False
    
    if "postgresql" not in database_url:
        print("❌ Esta migración es específica para PostgreSQL")
        print(f"Base de datos detectada: {database_url}")
        return False
    
    try:
        # Crear engine
        engine = create_engine(database_url)
        
        with engine.begin() as conn:
            print("Verificando estructura actual de la tabla users...")
            
            # Obtener columnas existentes
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """))
            
            existing_columns = {}
            for row in result:
                existing_columns[row[0]] = {
                    'type': row[1],
                    'nullable': row[2],
                    'default': row[3]
                }
            
            print(f"Columnas existentes: {list(existing_columns.keys())}")
            
            # Definir columnas nuevas a agregar
            new_columns = {
                'department': {
                    'sql': 'ALTER TABLE users ADD COLUMN department VARCHAR(100)',
                    'description': 'Departamento del usuario'
                },
                'auth_provider': {
                    'sql': 'ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) DEFAULT \'local\'',
                    'description': 'Proveedor de autenticación (local/ad)'
                },
                'ad_dn': {
                    'sql': 'ALTER TABLE users ADD COLUMN ad_dn TEXT',
                    'description': 'Distinguished Name de Active Directory'
                },
                'last_ad_sync': {
                    'sql': 'ALTER TABLE users ADD COLUMN last_ad_sync TIMESTAMP',
                    'description': 'Última sincronización con AD'
                },
                'updated_at': {
                    'sql': 'ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                    'description': 'Fecha de última actualización'
                }
            }
            
            # Agregar columnas que no existen
            added_columns = []
            for column_name, column_info in new_columns.items():
                if column_name not in existing_columns:
                    try:
                        print(f"\n📝 Agregando columna '{column_name}'...")
                        conn.execute(text(column_info['sql']))
                        print(f"✅ Columna '{column_name}' agregada: {column_info['description']}")
                        added_columns.append(column_name)
                    except Exception as e:
                        print(f"❌ Error agregando columna '{column_name}': {e}")
                else:
                    print(f"⚠️  Columna '{column_name}' ya existe")
            
            # Crear índices si no existen
            indexes = [
                {
                    'name': 'idx_users_auth_provider',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_users_auth_provider ON users(auth_provider)',
                    'description': 'Índice para proveedor de autenticación'
                },
                {
                    'name': 'idx_users_department',
                    'sql': 'CREATE INDEX IF NOT EXISTS idx_users_department ON users(department)',
                    'description': 'Índice para departamento'
                }
            ]
            
            print(f"\n📋 Creando índices...")
            for index in indexes:
                try:
                    conn.execute(text(index['sql']))
                    print(f"✅ Índice '{index['name']}' creado")
                except Exception as e:
                    print(f"⚠️  Índice '{index['name']}': {e}")
            
            # Actualizar valores por defecto para registros existentes
            if added_columns:
                print(f"\n🔄 Actualizando valores por defecto...")
                
                update_queries = [
                    {
                        'sql': "UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL",
                        'description': 'Marcar usuarios existentes como locales'
                    },
                    {
                        'sql': "UPDATE users SET updated_at = created_at WHERE updated_at IS NULL",
                        'description': 'Establecer fecha de actualización inicial'
                    }
                ]
                
                for update in update_queries:
                    try:
                        result = conn.execute(text(update['sql']))
                        affected_rows = result.rowcount
                        print(f"✅ {update['description']}: {affected_rows} filas actualizadas")
                    except Exception as e:
                        print(f"⚠️  Error en actualización: {e}")
        
        # Verificar resultado final
        print(f"\n🔍 Verificando estructura final...")
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """))
            
            final_columns = []
            for row in result:
                nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                default = f"DEFAULT {row[3]}" if row[3] else ""
                final_columns.append(f"{row[0]} ({row[1]}) {nullable} {default}".strip())
            
            print("Estructura final de la tabla users:")
            for i, col in enumerate(final_columns, 1):
                print(f"  {i:2d}. {col}")
        
        print(f"\n✅ MIGRACIÓN POSTGRESQL COMPLETADA EXITOSAMENTE")
        return True
        
    except Exception as e:
        print(f"❌ Error en migración PostgreSQL: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def verify_migration():
    """Verifica que la migración se aplicó correctamente"""
    print(f"\n=== VERIFICACIÓN DE MIGRACIÓN ===")
    
    try:
        database_url = os.getenv('DATABASE_URL')
        engine = create_engine(database_url)
        
        with engine.begin() as conn:
            # Contar usuarios existentes
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            total_users = result.scalar()
            
            # Verificar usuarios por proveedor de autenticación
            result = conn.execute(text("""
                SELECT auth_provider, COUNT(*) 
                FROM users 
                GROUP BY auth_provider
            """))
            
            auth_stats = dict(result.fetchall())
            
            print(f"📊 Estadísticas de usuarios:")
            print(f"   Total de usuarios: {total_users}")
            for provider, count in auth_stats.items():
                print(f"   Usuarios {provider}: {count}")
            
            # Verificar que podemos consultar las nuevas columnas
            result = conn.execute(text("""
                SELECT username, fullname, department, auth_provider 
                FROM users 
                LIMIT 3
            """))
            
            print(f"\n📋 Muestra de datos:")
            print("   Usuario | Nombre | Departamento | Auth Provider")
            print("   " + "-" * 50)
            
            for row in result:
                username = row[0] or "N/A"
                fullname = row[1] or "N/A"
                department = row[2] or "Sin asignar"
                auth_provider = row[3] or "local"
                print(f"   {username:<12} | {fullname:<15} | {department:<12} | {auth_provider}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return False

def create_test_ad_user():
    """Crea un usuario de prueba de AD"""
    print(f"\n=== CREANDO USUARIO DE PRUEBA AD ===")
    
    try:
        database_url = os.getenv('DATABASE_URL')
        engine = create_engine(database_url)
        
        with engine.begin() as conn:
            # Verificar si ya existe
            result = conn.execute(text("""
                SELECT COUNT(*) FROM users 
                WHERE username = 'su-jorge.romero' AND auth_provider = 'ad'
            """))
            
            if result.scalar() > 0:
                print("✅ Usuario de prueba AD ya existe")
                return True
            
            # Crear usuario de prueba
            conn.execute(text("""
                INSERT INTO users (
                    username, email, fullname, department, 
                    is_active, is_admin, auth_provider, ad_dn, 
                    password_hash, created_at, updated_at
                ) VALUES (
                    :username, :email, :fullname, :department,
                    :is_active, :is_admin, :auth_provider, :ad_dn,
                    NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """), {
                'username': 'su-jorge.romero',
                'email': 'su-jorge.romero@ikeasi.com',
                'fullname': 'Jorge Romero (AD)',
                'department': 'IT - Active Directory',
                'is_active': True,
                'is_admin': True,
                'auth_provider': 'ad',
                'ad_dn': 'CN=Jorge Romero,OU=IT,DC=ikeaspc,DC=ikeasi,DC=com'
            })
            
            print("✅ Usuario de prueba AD creado: su-jorge.romero")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando usuario de prueba: {e}")
        return False

def main():
    """Función principal"""
    print("🐘 MIGRACIÓN POSTGRESQL PARA ACTIVE DIRECTORY")
    print("=" * 60)
    
    # Ejecutar migración
    migration_success = run_postgresql_migration()
    
    if migration_success:
        # Verificar migración
        verification_success = verify_migration()
        
        if verification_success:
            # Crear usuario de prueba
            test_user_success = create_test_ad_user()
            
            print(f"\n🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print(f"\n📋 Próximos pasos:")
            print("1. ✅ Base de datos PostgreSQL actualizada")
            print("2. ✅ Nuevas columnas agregadas y verificadas")
            print("3. ✅ Índices creados para optimización")
            print("4. 🔄 Reiniciar aplicación para aplicar cambios")
            print("5. 🚀 Probar funcionalidad de importación AD")
            
            print(f"\n📝 Nuevas funcionalidades disponibles:")
            print("- Soporte para usuarios de Active Directory")
            print("- Diferenciación entre usuarios locales y AD")
            print("- Tracking de sincronizaciones con AD")
            print("- Campos adicionales (departamento, DN, etc.)")
        else:
            print(f"\n⚠️  Migración aplicada pero verificación falló")
    else:
        print(f"\n❌ MIGRACIÓN FALLÓ")
        print("Revisar errores mostrados arriba")
    
    return migration_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)