# test_ad_connection.py - Script para probar conexión con tu Active Directory

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_basic_connection():
    """Prueba conexión básica con Active Directory"""
    try:
        from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
        
        # Configuración desde .env
        ad_server = os.getenv("AD_SERVER", "ldap://172.19.2.241")
        ad_port = int(os.getenv("AD_PORT", "389"))
        ad_bind_dn = os.getenv("AD_BIND_DN")
        ad_bind_password = os.getenv("AD_BIND_PASSWORD")
        ad_base_dn = os.getenv("AD_BASE_DN")
        
        print("=== Configuración de Active Directory ===")
        print(f"Servidor: {ad_server}")
        print(f"Puerto: {ad_port}")
        print(f"Bind DN: {ad_bind_dn}")
        print(f"Base DN: {ad_base_dn}")
        print("=" * 50)
        
        # Paso 1: Crear servidor
        print("1. Creando servidor...")
        server = Server(ad_server, port=ad_port, get_info=ALL)
        print(f"✓ Servidor creado: {server}")
        
        # Paso 2: Probar conexión básica
        print("\n2. Probando conexión básica...")
        test_conn = Connection(server)
        if test_conn.bind():
            print("✓ Conexión básica exitosa")
            test_conn.unbind()
        else:
            print("✗ Fallo conexión básica")
            return False
        
        # Paso 3: Probar autenticación con credenciales
        print("\n3. Probando autenticación con credenciales...")
        auth_conn = Connection(
            server,
            user=ad_bind_dn,
            password=ad_bind_password,
            authentication=NTLM,
            auto_bind=True
        )
        
        if auth_conn.bound:
            print("✓ Autenticación exitosa")
            
            # Paso 4: Probar búsqueda básica
            print("\n4. Probando búsqueda básica...")
            auth_conn.search(
                search_base=ad_base_dn,
                search_filter='(objectClass=*)',
                search_scope=SUBTREE,
                attributes=['distinguishedName'],
                size_limit=5
            )
            
            print(f"✓ Búsqueda exitosa. Encontrados {len(auth_conn.entries)} objetos:")
            for entry in auth_conn.entries:
                print(f"  - {entry.distinguishedName}")
            
            # Paso 5: Buscar usuarios
            print("\n5. Buscando usuarios...")
            user_base_dn = os.getenv("AD_USER_BASE_DN")
            user_filter = os.getenv("AD_USER_FILTER")
            
            auth_conn.search(
                search_base=user_base_dn,
                search_filter=user_filter,
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName', 'mail'],
                size_limit=10
            )
            
            print(f"✓ Encontrados {len(auth_conn.entries)} usuarios:")
            for entry in auth_conn.entries:
                username = entry.sAMAccountName.value if hasattr(entry, 'sAMAccountName') else 'N/A'
                fullname = entry.displayName.value if hasattr(entry, 'displayName') else 'N/A'
                email = entry.mail.value if hasattr(entry, 'mail') else 'N/A'
                print(f"  - {username} | {fullname} | {email}")
            
            auth_conn.unbind()
            print("\n🎉 ¡Conexión con Active Directory exitosa!")
            return True
            
        else:
            print("✗ Fallo autenticación")
            print(f"Error: {auth_conn.result}")
            return False
            
    except ImportError:
        print("✗ Error: ldap3 no está instalado. Ejecutar: pip install ldap3")
        return False
    except Exception as e:
        print(f"✗ Error en conexión AD: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
        return False

def test_specific_user_search():
    """Buscar un usuario específico"""
    try:
        from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
        
        # Configuración
        ad_server = os.getenv("AD_SERVER")
        ad_port = int(os.getenv("AD_PORT", "389"))
        ad_bind_dn = os.getenv("AD_BIND_DN")
        ad_bind_password = os.getenv("AD_BIND_PASSWORD")
        user_base_dn = os.getenv("AD_USER_BASE_DN")
        
        # Conectar
        server = Server(ad_server, port=ad_port, get_info=ALL)
        conn = Connection(
            server,
            user=ad_bind_dn,
            password=ad_bind_password,
            authentication=NTLM,
            auto_bind=True
        )
        
        if conn.bound:
            print("\n=== Búsqueda de Usuario Específico ===")
            
            # Buscar por tu usuario
            search_filter = "(sAMAccountName=su-jorge.romero)"
            
            conn.search(
                search_base=user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['*']  # Obtener todos los atributos
            )
            
            if conn.entries:
                entry = conn.entries[0]
                print(f"✓ Usuario encontrado: {entry.distinguishedName}")
                print("\nAtributos disponibles:")
                for attr in entry.entry_attributes:
                    value = getattr(entry, attr).value if hasattr(entry, attr) else None
                    if value:
                        print(f"  {attr}: {value}")
            else:
                print("✗ Usuario no encontrado")
            
            conn.unbind()
        
    except Exception as e:
        print(f"✗ Error buscando usuario: {str(e)}")

def validate_configuration():
    """Validar configuración antes de probar"""
    print("=== Validación de Configuración ===")
    
    required_vars = [
        "AD_SERVER", "AD_BIND_DN", "AD_BIND_PASSWORD", 
        "AD_BASE_DN", "AD_USER_BASE_DN"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Ocultar contraseña en logs
            display_value = value if var != "AD_BIND_PASSWORD" else "*" * len(value)
            print(f"✓ {var}: {display_value}")
    
    if missing_vars:
        print(f"\n✗ Variables faltantes: {', '.join(missing_vars)}")
        return False
    
    print("✓ Configuración completa")
    return True

if __name__ == "__main__":
    print("🔍 Probando conexión con Active Directory...\n")
    
    # Validar configuración
    if not validate_configuration():
        exit(1)
    
    # Probar conexión
    if test_basic_connection():
        # Si la conexión básica funciona, probar búsqueda específica
        test_specific_user_search()
    else:
        print("\n❌ Conexión con Active Directory falló")
        print("\n🛠️  Pasos para solucionar:")
        print("1. Verificar que el servidor AD esté accesible:")
        print("   ping 172.19.2.241")
        print("2. Verificar puerto 389 abierto:")
        print("   telnet 172.19.2.241 389")
        print("3. Verificar credenciales de su-jorge.romero")
        print("4. Verificar estructura de DN en Active Directory")
        print("5. Instalar dependencias: pip install ldap3")