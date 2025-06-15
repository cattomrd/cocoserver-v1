# services/ad_service.py - Servicio final funcional para Active Directory

import logging
from typing import List, Dict, Optional, Tuple
from ldap3 import Server, Connection, ALL, NTLM, SIMPLE, SUBTREE
from ldap3.core.exceptions import LDAPException
import os

logger = logging.getLogger(__name__)

class ActiveDirectoryService:
    """Servicio para interactuar con Active Directory"""
    
    def __init__(self):
        self.server = None
        self.connection = None
        self._initialize_server()
    
    def _initialize_server(self):
        """Inicializa la conexión al servidor AD"""
        try:
            # Configurar servidor
            ad_server = os.getenv('AD_SERVER', '172.19.2.241')
            ad_port = int(os.getenv('AD_PORT', '389'))
            ad_use_ssl = os.getenv('AD_USE_SSL', 'false').lower() == 'true'
            
            self.server = Server(
                ad_server,
                port=ad_port,
                use_ssl=ad_use_ssl,
                get_info=ALL
            )
            
            logger.info(f"Servidor AD configurado: {ad_server}:{ad_port} (SSL: {ad_use_ssl})")
            
        except Exception as e:
            logger.error(f"Error configurando servidor AD: {str(e)}")
            raise
    
    def _get_connection(self) -> Connection:
        """Obtiene una conexión autenticada al AD usando SIMPLE authentication"""
        try:
            ad_bind_dn = os.getenv('AD_BIND_DN', 'su-jorge.romero@ikeasi.com')
            ad_bind_password = os.getenv('AD_BIND_PASSWORD')
            
            # Usar SIMPLE authentication (funciona según las pruebas)
            connection = Connection(
                self.server,
                user=ad_bind_dn,
                password=ad_bind_password,
                authentication=SIMPLE,
                auto_bind=True
            )
            
            if not connection.bound:
                raise Exception(f"No se pudo establecer conexión con AD. Resultado: {connection.result}")
            
            logger.info("Conexión exitosa con Active Directory usando SIMPLE auth")
            return connection
            
        except LDAPException as e:
            logger.error(f"Error de LDAP conectando a AD: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error conectando a AD: {str(e)}")
            raise
    
    def test_connection(self) -> Dict[str, any]:
        """Prueba la conexión con Active Directory"""
        try:
            connection = self._get_connection()
            
            # Probar búsqueda básica
            ad_base_dn = os.getenv('AD_BASE_DN', 'DC=ikeaspc,DC=ikeasi,DC=com')
            connection.search(
                search_base=ad_base_dn,
                search_filter='(objectClass=domain)',
                search_scope=SUBTREE,
                attributes=['distinguishedName', 'name'],
                size_limit=1
            )
            
            result = {
                'success': True,
                'message': 'Conexión exitosa con Active Directory',
                'server': os.getenv('AD_SERVER'),
                'auth_type': 'SIMPLE',
                'entries_found': len(connection.entries),
                'server_info': str(connection.server.info) if connection.server.info else 'N/A'
            }
            
            connection.unbind()
            logger.info("Prueba de conexión AD exitosa")
            return result
            
        except Exception as e:
            error_msg = f"Error en prueba de conexión AD: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg,
                'server': os.getenv('AD_SERVER'),
                'auth_type': 'SIMPLE',
                'entries_found': 0
            }
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Autentica un usuario contra Active Directory usando SIMPLE auth
        """
        try:
            # Buscar el usuario primero
            user_data = self.get_user_by_username(username)
            if not user_data:
                logger.warning(f"Usuario no encontrado en AD: {username}")
                return False, None
            
            # Probar autenticación directa con SIMPLE auth
            try:
                # Usar formato UPN para SIMPLE auth
                auth_username = f"{username}@{os.getenv('AD_DOMAIN_FQDN', 'ikeasi.com')}"
                
                auth_connection = Connection(
                    self.server,
                    user=auth_username,
                    password=password,
                    authentication=SIMPLE
                )
                
                if auth_connection.bind():
                    logger.info(f"Autenticación SIMPLE exitosa para: {auth_username}")
                    auth_connection.unbind()
                    return True, user_data
                else:
                    logger.warning(f"Autenticación SIMPLE falló para: {auth_username}")
                    
            except Exception as auth_error:
                logger.warning(f"Error en autenticación SIMPLE: {auth_error}")
                
                # Intentar con Distinguished Name si está disponible
                user_dn = user_data.get('dn')
                if user_dn:
                    try:
                        auth_connection = Connection(
                            self.server,
                            user=user_dn,
                            password=password,
                            authentication=SIMPLE
                        )
                        
                        if auth_connection.bind():
                            logger.info(f"Autenticación por DN exitosa para: {user_dn}")
                            auth_connection.unbind()
                            return True, user_data
                            
                    except Exception as dn_error:
                        logger.warning(f"Fallo autenticación por DN: {dn_error}")
            
            logger.warning(f"Todas las autenticaciones fallaron para usuario: {username}")
            return False, None
                
        except Exception as e:
            logger.error(f"Error autenticando usuario {username}: {str(e)}")
            return False, None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Obtiene información de un usuario por nombre de usuario"""
        try:
            connection = self._get_connection()
            
            # Construir filtro de búsqueda
            ad_user_filter = os.getenv('AD_USER_FILTER', 
                '(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))')
            ad_username_attr = os.getenv('AD_USERNAME_ATTRIBUTE', 'sAMAccountName')
            
            search_filter = f"(&{ad_user_filter}({ad_username_attr}={username}))"
            
            # Atributos a obtener
            attributes = [
                ad_username_attr,
                os.getenv('AD_EMAIL_ATTRIBUTE', 'mail'),
                os.getenv('AD_FULLNAME_ATTRIBUTE', 'displayName'),
                os.getenv('AD_DEPARTMENT_ATTRIBUTE', 'department'),
                'memberOf',
                'userAccountControl',
                'distinguishedName'
            ]
            
            # Realizar búsqueda
            ad_user_base_dn = os.getenv('AD_USER_BASE_DN', 'DC=ikeaspc,DC=ikeasi,DC=com')
            connection.search(
                search_base=ad_user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attributes
            )
            
            if connection.entries:
                entry = connection.entries[0]
                
                # Función helper para extraer valores
                def get_attr_value(entry, attr_name):
                    if hasattr(entry, attr_name):
                        value = getattr(entry, attr_name)
                        if isinstance(value, list) and len(value) > 0:
                            return str(value[0])
                        elif not isinstance(value, list):
                            return str(value)
                    return ''
                
                # Extraer información del usuario
                user_data = {
                    'dn': str(entry.distinguishedName),
                    'username': get_attr_value(entry, ad_username_attr),
                    'email': get_attr_value(entry, os.getenv('AD_EMAIL_ATTRIBUTE', 'mail')),
                    'fullname': get_attr_value(entry, os.getenv('AD_FULLNAME_ATTRIBUTE', 'displayName')),
                    'department': get_attr_value(entry, os.getenv('AD_DEPARTMENT_ATTRIBUTE', 'department')),
                    'groups': [str(group) for group in getattr(entry, 'memberOf', [])],
                    'is_enabled': not bool(int(getattr(entry, 'userAccountControl', [0])[0] if hasattr(entry, 'userAccountControl') else 0) & 2)
                }
                
                connection.unbind()
                logger.info(f"Usuario encontrado en AD: {username}")
                return user_data
            else:
                connection.unbind()
                logger.warning(f"Usuario no encontrado en AD: {username}")
                return None
                
        except Exception as e:
            logger.error(f"Error buscando usuario {username}: {str(e)}")
            return None
    
    def search_users(self, query: str, limit: int = 50) -> List[Dict]:
        """Busca usuarios en AD por diferentes criterios"""
        try:
            connection = self._get_connection()
            
            # Construir filtro de búsqueda flexible
            ad_user_filter = os.getenv('AD_USER_FILTER', 
                '(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))')
            
            search_criteria = [
                f"(sAMAccountName=*{query}*)",
                f"(displayName=*{query}*)",
                f"(mail=*{query}*)",
                f"(givenName=*{query}*)",
                f"(sn=*{query}*)"
            ]
            
            search_filter = f"(&{ad_user_filter}(|{''.join(search_criteria)}))"
            
            # Realizar búsqueda
            ad_user_base_dn = os.getenv('AD_USER_BASE_DN', 'DC=ikeaspc,DC=ikeasi,DC=com')
            connection.search(
                search_base=ad_user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName', 'mail', 'department', 'distinguishedName'],
                size_limit=limit
            )
            
            users = []
            for entry in connection.entries:
                # Función helper para extraer valores
                def get_attr_value(entry, attr_name):
                    if hasattr(entry, attr_name):
                        value = getattr(entry, attr_name)
                        if isinstance(value, list) and len(value) > 0:
                            return str(value[0])
                        elif not isinstance(value, list):
                            return str(value)
                    return ''
                
                users.append({
                    'username': get_attr_value(entry, 'sAMAccountName'),
                    'fullname': get_attr_value(entry, 'displayName'),
                    'email': get_attr_value(entry, 'mail'),
                    'department': get_attr_value(entry, 'department'),
                    'dn': str(entry.distinguishedName)
                })
            
            connection.unbind()
            logger.info(f"Búsqueda AD completada: {len(users)} usuarios encontrados")
            return users
            
        except Exception as e:
            logger.error(f"Error en búsqueda de usuarios: {str(e)}")
            return []
    
    def get_all_users(self, limit: int = 1000) -> List[Dict]:
        """Obtiene todos los usuarios activos de AD"""
        try:
            connection = self._get_connection()
            
            # Filtro para usuarios activos
            ad_user_filter = os.getenv('AD_USER_FILTER', 
                '(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))')
            
            # Realizar búsqueda
            ad_user_base_dn = os.getenv('AD_USER_BASE_DN', 'DC=ikeaspc,DC=ikeasi,DC=com')
            connection.search(
                search_base=ad_user_base_dn,
                search_filter=ad_user_filter,
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName', 'mail', 'department', 'distinguishedName'],
                size_limit=limit
            )
            
            users = []
            for entry in connection.entries:
                # Función helper para extraer valores
                def get_attr_value(entry, attr_name):
                    if hasattr(entry, attr_name):
                        value = getattr(entry, attr_name)
                        if isinstance(value, list) and len(value) > 0:
                            return str(value[0])
                        elif not isinstance(value, list):
                            return str(value)
                    return ''
                
                users.append({
                    'username': get_attr_value(entry, 'sAMAccountName'),
                    'fullname': get_attr_value(entry, 'displayName'),
                    'email': get_attr_value(entry, 'mail'),
                    'department': get_attr_value(entry, 'department'),
                    'dn': str(entry.distinguishedName)
                })
            
            connection.unbind()
            logger.info(f"Obtención de usuarios AD completada: {len(users)} usuarios")
            return users
            
        except Exception as e:
            logger.error(f"Error obteniendo todos los usuarios: {str(e)}")
            return []

# Instancia global del servicio
ad_service = ActiveDirectoryService()