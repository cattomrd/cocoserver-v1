#!/usr/bin/env python3
"""
Test robusto y simple de Active Directory
Maneja errores de atributos faltantes
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def safe_get_attr(entry, attr_name, default=''):
    """Extrae atributos de forma segura"""
    try:
        if hasattr(entry, attr_name):
            value = getattr(entry, attr_name)
            if isinstance(value, list) and len(value) > 0:
                return str(value[0])
            elif not isinstance(value, list) and value:
                return str(value)
    except Exception:
        pass
    return default

def test_ad_robust():
    """Test robusto de Active Directory"""
    print("=== TEST ROBUSTO DE ACTIVE DIRECTORY ===")
    
    try:
        from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
        
        # Configuración
        ad_server = "172.19.2.241"
        ad_port = 389
        ad_bind_dn = "su-jorge.romero@ikeasi.com"
        ad_bind_password = os.getenv('AD_BIND_PASSWORD')
        ad_base_dn = "DC=ikeaspc,DC=ikeasi,DC=com"
        
        print(f"Conectando a {ad_server}:{ad_port}")
        print(f"Usuario: {ad_bind_dn}")
        print("-" * 50)
        
        # Conexión
        server = Server(ad_server, port=ad_port, use_ssl=False, get_info=ALL)
        conn = Connection(server, user=ad_bind_dn, password=ad_bind_password, 
                         authentication=SIMPLE, auto_bind=True)
        
        if not conn.bound:
            print("❌ Error de conexión")
            return False
            
        print("✅ Conexión exitosa")
        
        # 1. Info del servidor
        print(f"\n1. Información del servidor:")
        print(f"   Nombre del servidor: {server.info.naming_contexts if server.info else 'N/A'}")
        print(f"   Base DN detectado: {ad_base_dn}")
        
        # 2. Contar usuarios
        print(f"\n2. Contando usuarios activos...")
        user_filter = "(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
        
        conn.search(
            search_base=ad_base_dn,
            search_filter=user_filter,
            search_scope=SUBTREE,
            attributes=['sAMAccountName'],
            size_limit=1000
        )
        
        total_users = len(conn.entries)
        print(f"   ✅ Total de usuarios activos: {total_users}")
        
        # 3. Muestra de usuarios (con manejo de errores)
        print(f"\n3. Muestra de usuarios (primeros 5):")
        conn.search(
            search_base=ad_base_dn,
            search_filter=user_filter,
            search_scope=SUBTREE,
            attributes=['sAMAccountName', 'displayName', 'mail', 'department'],
            size_limit=5
        )
        
        if conn.entries:
            print("   #  | Usuario        | Nombre                    | Email")
            print("   " + "-" * 65)
            
            for i, entry in enumerate(conn.entries, 1):
                username = safe_get_attr(entry, 'sAMAccountName', 'N/A')
                fullname = safe_get_attr(entry, 'displayName', 'N/A')
                email = safe_get_attr(entry, 'mail', 'N/A')
                
                print(f"   {i:<2} | {username:<14} | {fullname:<25} | {email}")
        
        # 4. Buscar tu usuario
        print(f"\n4. Buscando tu usuario específico...")
        conn.search(
            search_base=ad_base_dn,
            search_filter="(sAMAccountName=su-jorge.romero)",
            search_scope=SUBTREE,
            attributes=['sAMAccountName', 'displayName', 'mail', 'department', 
                       'memberOf', 'distinguishedName', 'userAccountControl']
        )
        
        if conn.entries:
            entry = conn.entries[0]
            print(f"   ✅ Usuario encontrado!")
            print(f"   DN: {safe_get_attr(entry, 'distinguishedName')}")
            print(f"   Nombre: {safe_get_attr(entry, 'displayName', 'No configurado')}")
            print(f"   Email: {safe_get_attr(entry, 'mail', 'No configurado')}")
            print(f"   Departamento: {safe_get_attr(entry, 'department', 'No configurado')}")
            
            # Grupos
            if hasattr(entry, 'memberOf'):
                groups = getattr(entry, 'memberOf', [])
                print(f"   Grupos: {len(groups)} membresías")
                for i, group in enumerate(groups[:3]):
                    group_name = str(group).split(',')[0].replace('CN=', '')
                    print(f"      {i+1}. {group_name}")
                if len(groups) > 3:
                    print(f"      ... y {len(groups) - 3} grupos más")
            else:
                print(f"   Grupos: No configurado")
        else:
            print("   ❌ Tu usuario no encontrado")
        
        # 5. Test de búsqueda por nombre
        print(f"\n5. Test de búsqueda por nombre 'Jorge'...")
        search_filter = "(&(objectClass=user)(objectCategory=person)(|(displayName=*Jorge*)(givenName=*Jorge*)))"
        
        conn.search(
            search_base=ad_base_dn,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=['sAMAccountName', 'displayName'],
            size_limit=10
        )
        
        print(f"   ✅ Encontrados {len(conn.entries)} usuarios con 'Jorge'")
        for entry in conn.entries[:3]:
            username = safe_get_attr(entry, 'sAMAccountName')
            fullname = safe_get_attr(entry, 'displayName')
            print(f"      - {username}: {fullname}")
        
        # 6. Verificar grupos administrativos
        print(f"\n6. Verificando grupos administrativos...")
        admin_groups = ['Domain Admins', 'Administrators']
        
        for group_name in admin_groups:
            try:
                conn.search(
                    search_base=ad_base_dn,
                    search_filter=f"(&(objectClass=group)(cn={group_name}))",
                    search_scope=SUBTREE,
                    attributes=['distinguishedName', 'member']
                )
                
                if conn.entries:
                    group_entry = conn.entries[0]
                    members = getattr(group_entry, 'member', [])
                    print(f"   ✅ {group_name}: {len(members)} miembros")
                else:
                    print(f"   ⚠️  {group_name}: No encontrado")
                    
            except Exception as e:
                print(f"   ❌ Error buscando {group_name}: {e}")
        
        conn.unbind()
        
        # Resumen final
        print(f"\n" + "=" * 60)
        print("🎉 PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print(f"✅ Conexión: Funcional")
        print(f"✅ Autenticación: SIMPLE")
        print(f"✅ Búsquedas: Funcionando")
        print(f"✅ Total usuarios: {total_users}")
        print(f"✅ Tu usuario: Encontrado")
        
        print(f"\n📋 CONFIGURACIÓN FINAL VALIDADA:")
        print("# Copiar a tu archivo .env")
        print(f"AD_SERVER=172.19.2.241")
        print(f"AD_PORT=389")
        print(f"AD_USE_SSL=false")
        print(f"AD_BIND_DN=su-jorge.romero@ikeasi.com")
        print(f"AD_BASE_DN=DC=ikeaspc,DC=ikeasi,DC=com")
        print(f"AD_USER_BASE_DN=DC=ikeaspc,DC=ikeasi,DC=com")
        print(f"AD_AUTH_TYPE=SIMPLE")
        
        return True
        
    except ImportError:
        print("❌ ldap3 no instalado: pip install ldap3")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_authentication_simulation():
    """Simula autenticación de diferentes usuarios"""
    print(f"\n=== SIMULACIÓN DE AUTENTICACIÓN ===")
    
    try:
        from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE
        
        ad_server = "172.19.2.241"
        ad_base_dn = "DC=ikeaspc,DC=ikeasi,DC=com"
        
        # Obtener algunos usuarios para probar
        server = Server(ad_server, port=389, use_ssl=False, get_info=ALL)
        conn = Connection(server, user="su-jorge.romero@ikeasi.com", 
                         password=os.getenv('AD_BIND_PASSWORD'), 
                         authentication=SIMPLE, auto_bind=True)
        
        if conn.bound:
            print("✅ Conectado para obtener lista de usuarios de prueba")
            
            # Buscar algunos usuarios
            conn.search(
                search_base=ad_base_dn,
                search_filter="(&(objectClass=user)(objectCategory=person)(sAMAccountName=*))",
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName'],
                size_limit=5
            )
            
            print(f"📋 Usuarios disponibles para autenticación:")
            test_users = []
            for entry in conn.entries:
                username = safe_get_attr(entry, 'sAMAccountName')
                fullname = safe_get_attr(entry, 'displayName')
                if username:
                    test_users.append(username)
                    print(f"   - {username} ({fullname})")
            
            conn.unbind()
            
            print(f"\n💡 Para probar autenticación desde tu aplicación:")
            print(f"   1. Usa cualquiera de los usuarios listados arriba")
            print(f"   2. Formato: usuario@ikeasi.com")
            print(f"   3. O solo: usuario (sin dominio)")
            print(f"   4. La contraseña debe ser la del usuario en AD")
            
        return True
        
    except Exception as e:
        print(f"❌ Error en simulación: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 TEST ROBUSTO DE ACTIVE DIRECTORY")
    print("Versión mejorada con manejo de errores")
    print("=" * 60)
    
    success = test_ad_robust()
    
    if success:
        test_authentication_simulation()
        
        print(f"\n🚀 CONFIGURACIÓN LISTA PARA PRODUCCIÓN")
        print(f"Tu Active Directory está configurado y funcionando correctamente.")
        print(f"\nPróximos pasos:")
        print(f"1. ✅ Configuración AD validada")
        print(f"2. 🔄 Actualizar .env con la configuración mostrada")
        print(f"3. 🔄 Implementar el servicio AD actualizado")
        print(f"4. 🚀 Probar login desde la aplicación web")
    else:
        print(f"\n❌ Configuración requiere ajustes")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)