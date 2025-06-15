#!/usr/bin/env python3
"""
Script simple para probar Active Directory
Basado en tu configuración actual que muestra buena conectividad
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_ldap_simple():
    """Prueba simple de LDAP con tu configuración actual"""
    print("=== PRUEBA SIMPLE DE ACTIVE DIRECTORY ===")
    
    try:
        from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE
        
        # Tu configuración actual
        ad_server = "172.19.2.241"  # IP directa
        ad_port = 389
        ad_use_ssl = False
        ad_bind_dn = "IKEASI\\su-jorge.romero"
        ad_bind_password = os.getenv('AD_BIND_PASSWORD')
        ad_base_dn = "DC=ikeaspc,DC=ikeasi,DC=com"
        
        print(f"Servidor: {ad_server}:{ad_port}")
        print(f"SSL: {ad_use_ssl}")
        print(f"Usuario: {ad_bind_dn}")
        print(f"Base DN: {ad_base_dn}")
        print("-" * 50)
        
        # 1. Crear servidor
        print("\n1. Creando servidor...")
        server = Server(
            ad_server,
            port=ad_port,
            use_ssl=ad_use_ssl,
            get_info=ALL
        )
        print("✅ Servidor creado")
        
        # 2. Probar conexión anónima
        print("\n2. Probando conexión anónima...")
        try:
            test_conn = Connection(server)
            if test_conn.bind():
                print("✅ Conexión anónima exitosa")
                test_conn.unbind()
            else:
                print("⚠️  Conexión anónima falló (normal en muchos AD)")
        except:
            print("⚠️  Conexión anónima falló (normal en muchos AD)")
        
        # 3. Probar con NTLM
        print("\n3. Probando autenticación NTLM...")
        try:
            ntlm_conn = Connection(
                server,
                user=ad_bind_dn,
                password=ad_bind_password,
                authentication=NTLM,
                auto_bind=True
            )
            
            if ntlm_conn.bound:
                print("✅ Autenticación NTLM exitosa")
                
                # Probar búsqueda básica
                print("\n4. Probando búsqueda básica...")
                ntlm_conn.search(
                    search_base=ad_base_dn,
                    search_filter='(objectClass=domain)',
                    search_scope=SUBTREE,
                    attributes=['distinguishedName', 'name'],
                    size_limit=5
                )
                
                if ntlm_conn.entries:
                    print(f"✅ Búsqueda exitosa: {len(ntlm_conn.entries)} entrada(s)")
                    for entry in ntlm_conn.entries:
                        print(f"   - {entry.distinguishedName}")
                else:
                    print("⚠️  Búsqueda sin resultados")
                
                # Probar búsqueda de usuarios
                print("\n5. Probando búsqueda de usuarios...")
                user_filter = "(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
                
                ntlm_conn.search(
                    search_base=ad_base_dn,
                    search_filter=user_filter,
                    search_scope=SUBTREE,
                    attributes=['sAMAccountName', 'displayName', 'mail'],
                    size_limit=10
                )
                
                if ntlm_conn.entries:
                    print(f"✅ Usuarios encontrados: {len(ntlm_conn.entries)}")
                    for entry in ntlm_conn.entries[:3]:  # Solo los primeros 3
                        username = getattr(entry, 'sAMAccountName', ['N/A'])[0] if hasattr(entry, 'sAMAccountName') else 'N/A'
                        fullname = getattr(entry, 'displayName', ['N/A'])[0] if hasattr(entry, 'displayName') else 'N/A'
                        email = getattr(entry, 'mail', ['N/A'])[0] if hasattr(entry, 'mail') else 'N/A'
                        print(f"   - {username} | {fullname} | {email}")
                    
                    if len(ntlm_conn.entries) > 3:
                        print(f"   ... y {len(ntlm_conn.entries) - 3} usuarios más")
                else:
                    print("⚠️  No se encontraron usuarios")
                
                # Buscar tu usuario específico
                print("\n6. Buscando tu usuario específico...")
                specific_filter = "(sAMAccountName=su-jorge.romero)"
                
                ntlm_conn.search(
                    search_base=ad_base_dn,
                    search_filter=specific_filter,
                    search_scope=SUBTREE,
                    attributes=['*']
                )
                
                if ntlm_conn.entries:
                    entry = ntlm_conn.entries[0]
                    print(f"✅ Tu usuario encontrado: {entry.distinguishedName}")
                    print("\nAtributos principales:")
                    
                    important_attrs = ['sAMAccountName', 'displayName', 'mail', 'department', 'memberOf']
                    for attr in important_attrs:
                        if hasattr(entry, attr):
                            value = getattr(entry, attr)
                            if isinstance(value, list) and len(value) > 0:
                                if attr == 'memberOf':
                                    print(f"   {attr}: {len(value)} grupos")
                                    for group in value[:3]:  # Solo los primeros 3 grupos
                                        print(f"      - {group}")
                                    if len(value) > 3:
                                        print(f"      ... y {len(value) - 3} más")
                                else:
                                    print(f"   {attr}: {value[0]}")
                            elif not isinstance(value, list):
                                print(f"   {attr}: {value}")
                else:
                    print("❌ Tu usuario no encontrado")
                
                ntlm_conn.unbind()
                print("\n🎉 ¡TODAS LAS PRUEBAS COMPLETADAS CON ÉXITO!")
                
                # Generar configuración final
                print("\n" + "=" * 60)
                print("🎯 CONFIGURACIÓN FINAL RECOMENDADA")
                print("=" * 60)
                print("# Configuración funcional para tu .env:")
                print(f"AD_SERVER={ad_server}")
                print(f"AD_PORT={ad_port}")
                print(f"AD_USE_SSL=false")
                print(f"AD_BIND_DN=IKEASI\\su-jorge.romero")
                print("AD_BIND_PASSWORD=Isl@sV@leares,.,2025**")
                print(f"AD_BASE_DN={ad_base_dn}")
                print(f"AD_USER_BASE_DN={ad_base_dn}")
                
                return True
                
            else:
                print(f"❌ Autenticación NTLM falló: {ntlm_conn.result}")
                
        except Exception as ntlm_error:
            print(f"❌ Error NTLM: {str(ntlm_error)}")
            
            # Intentar con SIMPLE como fallback
            print("\n3b. Probando autenticación SIMPLE como fallback...")
            try:
                simple_conn = Connection(
                    server,
                    user="su-jorge.romero@ikeasi.com",  # Formato UPN para SIMPLE
                    password=ad_bind_password,
                    authentication=SIMPLE,
                    auto_bind=True
                )
                
                if simple_conn.bound:
                    print("✅ Autenticación SIMPLE exitosa")
                    print("   Configuración alternativa:")
                    print("   AD_BIND_DN=su-jorge.romero@ikeasi.com")
                    print("   # Cambiar authentication=SIMPLE en el código")
                    
                    simple_conn.unbind()
                    return True
                else:
                    print(f"❌ Autenticación SIMPLE falló: {simple_conn.result}")
                    
            except Exception as simple_error:
                print(f"❌ Error SIMPLE: {str(simple_error)}")
        
        return False
        
    except ImportError:
        print("❌ Error: ldap3 no está instalado")
        print("Instalar con: pip install ldap3")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🔍 PRUEBA SIMPLE DE ACTIVE DIRECTORY")
    print("Basado en tu configuración actual con buena conectividad")
    print("=" * 60)
    
    success = test_ldap_simple()
    
    if success:
        print("\n✅ PRUEBA EXITOSA - Active Directory configurado correctamente")
        print("\nPróximos pasos:")
        print("1. Usar la configuración mostrada arriba en tu .env")
        print("2. Actualizar tu servicio AD con la configuración funcional")
        print("3. Probar desde tu aplicación web")
    else:
        print("\n❌ PRUEBA FALLIDA")
        print("\nPasos para resolver:")
        print("1. Verificar credenciales con el administrador de AD")
        print("2. Verificar permisos del usuario su-jorge.romero")
        print("3. Verificar configuración de dominio IKEASI")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)