#!/usr/bin/env python3
"""
Script de diagnóstico para problemas SSL/LDAP con Active Directory
"""

import os
import socket
import ssl
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_network_connectivity():
    """Probar conectividad de red a diferentes puertos"""
    print("=== PRUEBA DE CONECTIVIDAD DE RED ===")
    
    ad_server = os.getenv('AD_SERVER', 'ikeaspc.ikeasi.com')
    ports_to_test = [389, 636, 3268, 3269]  # LDAP, LDAPS, Global Catalog
    
    results = {}
    
    for port in ports_to_test:
        print(f"\nProbando {ad_server}:{port}...")
        
        try:
            # Crear socket con timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            # Intentar conectar
            result = sock.connect_ex((ad_server, port))
            
            if result == 0:
                print(f"✅ Puerto {port}: Abierto y accesible")
                results[port] = "success"
                
                # Para puerto SSL, probar handshake SSL
                if port in [636, 3269]:
                    try:
                        # Crear contexto SSL
                        context = ssl.create_default_context()
                        # Deshabilitar verificación de certificado para prueba
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                        
                        # Envolver socket con SSL
                        ssl_sock = context.wrap_socket(sock, server_hostname=ad_server)
                        print(f"✅ Puerto {port}: SSL Handshake exitoso")
                        ssl_sock.close()
                        results[port] = "ssl_success"
                        
                    except ssl.SSLError as ssl_err:
                        print(f"❌ Puerto {port}: SSL Handshake falló - {ssl_err}")
                        results[port] = "ssl_failed"
                    except Exception as ssl_ex:
                        print(f"❌ Puerto {port}: Error SSL - {ssl_ex}")
                        results[port] = "ssl_error"
            else:
                print(f"❌ Puerto {port}: Cerrado o inaccesible")
                results[port] = "closed"
                
            sock.close()
            
        except socket.gaierror as e:
            print(f"❌ Puerto {port}: Error de resolución DNS - {e}")
            results[port] = "dns_error"
        except Exception as e:
            print(f"❌ Puerto {port}: Error de conexión - {e}")
            results[port] = "connection_error"
    
    return results

def test_ldap_connections():
    """Probar conexiones LDAP con diferentes configuraciones"""
    print("\n=== PRUEBA DE CONEXIONES LDAP ===")
    
    try:
        from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE
        
        # Configuración base
        ad_server = os.getenv('AD_SERVER')
        ad_bind_dn = os.getenv('AD_BIND_DN')
        ad_bind_password = os.getenv('AD_BIND_PASSWORD')
        ad_base_dn = os.getenv('AD_BASE_DN')
        
        # Configuraciones a probar
        test_configs = [
            {
                'name': 'LDAP Sin SSL (Puerto 389)',
                'port': 389,
                'use_ssl': False,
                'auth': NTLM,
                'auth_name': 'NTLM'
            },
            {
                'name': 'LDAPS con SSL (Puerto 636)',
                'port': 636,
                'use_ssl': True,
                'auth': NTLM,
                'auth_name': 'NTLM'
            },
            {
                'name': 'LDAP Sin SSL con SIMPLE Auth',
                'port': 389,
                'use_ssl': False,
                'auth': SIMPLE,
                'auth_name': 'SIMPLE'
            }
        ]
        
        successful_configs = []
        
        for config in test_configs:
            print(f"\n🔍 Probando: {config['name']}")
            print(f"   Puerto: {config['port']}")
            print(f"   SSL: {config['use_ssl']}")
            print(f"   Auth: {config['auth_name']}")
            
            try:
                # Crear servidor
                server = Server(
                    ad_server,
                    port=config['port'],
                    use_ssl=config['use_ssl'],
                    get_info=ALL
                )
                
                # Formato de usuario según autenticación
                if config['auth'] == NTLM:
                    # Convertir a formato NETBIOS si es necesario
                    if '@' in ad_bind_dn:
                        username = ad_bind_dn.split('@')[0]
                        domain = os.getenv('AD_DOMAIN', 'IKEASI')
                        user = f"{domain}\\{username}"
                    else:
                        user = ad_bind_dn
                else:
                    user = ad_bind_dn
                
                print(f"   Usuario: {user}")
                
                # Crear conexión
                connection = Connection(
                    server,
                    user=user,
                    password=ad_bind_password,
                    authentication=config['auth'],
                    auto_bind=True
                )
                
                if connection.bound:
                    print(f"   ✅ Conexión exitosa")
                    
                    # Probar búsqueda básica
                    connection.search(
                        search_base=ad_base_dn,
                        search_filter='(objectClass=domain)',
                        search_scope=SUBTREE,
                        attributes=['distinguishedName'],
                        size_limit=1
                    )
                    
                    if connection.entries:
                        print(f"   ✅ Búsqueda exitosa: {len(connection.entries)} entrada(s)")
                        successful_configs.append(config)
                    else:
                        print(f"   ⚠️  Conexión OK pero búsqueda sin resultados")
                    
                    connection.unbind()
                else:
                    print(f"   ❌ Fallo de conexión: {connection.result}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        return successful_configs
        
    except ImportError:
        print("❌ Error: ldap3 no está instalado")
        print("Instalar con: pip install ldap3")
        return []

def generate_recommendations(network_results, ldap_results):
    """Generar recomendaciones basadas en las pruebas"""
    print("\n" + "=" * 60)
    print("🎯 RECOMENDACIONES")
    print("=" * 60)
    
    # Analizar resultados de red
    if network_results.get(389) == "success":
        print("✅ Puerto 389 (LDAP) disponible - Usar conexiones sin SSL")
        print("   Configuración recomendada:")
        print("   AD_USE_SSL=false")
        print("   AD_PORT=389")
    
    if network_results.get(636) == "ssl_success":
        print("\n✅ Puerto 636 (LDAPS) disponible - SSL funcional")
        print("   Configuración recomendada para SSL:")
        print("   AD_USE_SSL=true")
        print("   AD_PORT=636")
    elif network_results.get(636) == "ssl_failed":
        print("\n⚠️  Puerto 636 abierto pero SSL falla")
        print("   Posibles causas:")
        print("   - Certificado SSL inválido o expirado")
        print("   - Configuración SSL del servidor AD incorrecta")
        print("   - Necesita configuración de certificados del cliente")
    
    # Analizar resultados LDAP
    if ldap_results:
        print(f"\n✅ {len(ldap_results)} configuración(es) LDAP exitosa(s):")
        
        for config in ldap_results:
            print(f"\n🎯 CONFIGURACIÓN FUNCIONAL:")
            print(f"   AD_USE_SSL={str(config['use_ssl']).lower()}")
            print(f"   AD_PORT={config['port']}")
            print(f"   # Autenticación: {config['auth_name']}")
            
            if config['auth'] == NTLM:
                print(f"   AD_BIND_DN=IKEASI\\su-jorge.romero")
            else:
                print(f"   AD_BIND_DN=su-jorge.romero@ikeasi.com")
            
            break  # Mostrar solo la primera configuración exitosa
    else:
        print("\n❌ NINGUNA CONFIGURACIÓN LDAP FUNCIONAL")
        print("\n🛠️  PASOS PARA SOLUCIONAR:")
        
        if network_results.get(389) != "success":
            print("1. Verificar conectividad de red:")
            print("   ping ikeaspc.ikeasi.com")
            print("   telnet ikeaspc.ikeasi.com 389")
        
        print("2. Verificar credenciales del usuario de servicio")
        print("3. Verificar permisos del usuario en Active Directory")
        print("4. Verificar configuración de firewall")
        print("5. Contactar al administrador de Active Directory")

def main():
    """Función principal del diagnóstico"""
    print("🔍 DIAGNÓSTICO COMPLETO SSL/LDAP PARA ACTIVE DIRECTORY")
    print("=" * 60)
    
    # Mostrar configuración actual
    print("=== CONFIGURACIÓN ACTUAL ===")
    print(f"Servidor: {os.getenv('AD_SERVER')}")
    print(f"Puerto: {os.getenv('AD_PORT')}")
    print(f"SSL: {os.getenv('AD_USE_SSL')}")
    print(f"Usuario: {os.getenv('AD_BIND_DN')}")
    print("-" * 60)
    
    # Probar conectividad de red
    network_results = test_network_connectivity()
    
    # Probar conexiones LDAP
    ldap_results = test_ldap_connections()
    
    # Generar recomendaciones
    generate_recommendations(network_results, ldap_results)
    
    # Determinar éxito general
    success = len(ldap_results) > 0
    
    if success:
        print("\n🎉 DIAGNÓSTICO COMPLETADO - Al menos una configuración funciona")
    else:
        print("\n❌ DIAGNÓSTICO FALLIDO - Revisar configuración y red")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)