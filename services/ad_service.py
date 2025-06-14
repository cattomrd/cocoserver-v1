# services/ad_service.py - Servicio para interactuar con Active Directory

import logging
from typing import List, Dict, Optional, Tuple
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
from ldap3.core.exceptions import LDAPException
import re

from config.ad_config import ad_settings

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
            port = ad_settings.AD_SSL_PORT if ad_settings.AD_USE_SSL else ad_settings.AD_PORT
            use_ssl = ad_settings.AD_USE_SSL
            
            self.server = Server(
                ad_settings.AD_SERVER,
                port=port,
                use_ssl=use_ssl,
                get_info=ALL
            )
            
            logger.info(f"Servidor AD configurado: {ad_settings.AD_SERVER}:{port} (SSL: {use_ssl})")
            
        except Exception as e:
            logger.error(f"Error configurando servidor AD: {str(e)}")
            raise
    
    def _get_connection(self) -> Connection:
        """Obtiene una conexión autenticada al AD"""
        try:
            # Crear conexión con credenciales de servicio
            connection = Connection(
                self.server,
                user=ad_settings.AD_BIND_DN,
                password=ad_settings.AD_BIND_PASSWORD,
                authentication=NTLM,
                auto_bind=True
            )
            
            if not connection.bound:
                raise Exception("No se pudo establecer conexión con AD")
            
            return connection
            
        except LDAPException as e:
            logger.error(f"Error de LDAP conectando a AD: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error conectando a AD: {str(e)}")
            raise
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Autentica un usuario contra Active Directory
        
        Returns:
            Tuple[bool, Optional[Dict]]: (éxito, datos_usuario)
        """
        try:
            # Buscar el usuario primero
            user_data = self.get_user_by_username(username)
            if not user_data:
                logger.warning(f"Usuario no encontrado en AD: {username}")
                return False, None
            
            # Obtener el DN del usuario
            user_dn = user_data.get('dn')
            if not user_dn:
                logger.error(f"DN no encontrado para usuario: {username}")
                return False, None
            
            # Intentar autenticar con las credenciales del usuario
            auth_connection = Connection(
                self.server,
                user=user_dn,
                password=password,
                authentication=NTLM
            )
            
            if auth_connection.bind():
                logger.info(f"Autenticación exitosa para usuario: {username}")
                auth_connection.unbind()
                return True, user_data
            else:
                logger.warning(f"Autenticación fallida para usuario: {username}")
                return False, None
                
        except Exception as e:
            logger.error(f"Error autenticando usuario {username}: {str(e)}")
            return False, None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Obtiene información de un usuario por nombre de usuario"""
        try:
            connection = self._get_connection()
            
            # Construir filtro de búsqueda
            search_filter = f"(&{ad_settings.AD_USER_FILTER}({ad_settings.AD_USERNAME_ATTRIBUTE}={username}))"
            
            # Atributos a obtener
            attributes = [
                ad_settings.AD_USERNAME_ATTRIBUTE,
                ad_settings.AD_EMAIL_ATTRIBUTE,
                ad_settings.AD_FULLNAME_ATTRIBUTE,
                ad_settings.AD_DEPARTMENT_ATTRIBUTE,
                'memberOf',
                'userAccountControl',
                'distinguishedName'
            ]
            
            # Realizar búsqueda
            connection.search(
                search_base=ad_settings.AD_USER_BASE_DN,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attributes
            )
            
            if connection.entries:
                entry = connection.entries[0]
                user_data = self._format_user_data(entry)
                connection.unbind()
                return user_data
            else:
                logger.warning(f"Usuario no encontrado: {username}")
                connection.unbind()
                return None
                
        except Exception as e:
            logger.error(f"Error buscando usuario {username}: {str(e)}")
            return None
    
    def get_all_users(self, page_size: int = 1000) -> List[Dict]:
        """Obtiene todos los usuarios del AD"""
        try:
            connection = self._get_connection()
            users = []
            
            # Configurar paginación
            connection.search(
                search_base=ad_settings.AD_USER_BASE_DN,
                search_filter=ad_settings.AD_USER_FILTER,
                search_scope=SUBTREE,
                attributes=[
                    ad_settings.AD_USERNAME_ATTRIBUTE,
                    ad_settings.AD_EMAIL_ATTRIBUTE,
                    ad_settings.AD_FULLNAME_ATTRIBUTE,
                    ad_settings.AD_DEPARTMENT_ATTRIBUTE,
                    'memberOf',
                    'userAccountControl',
                    'distinguishedName'
                ],
                paged_size=page_size
            )
            
            # Procesar resultados
            for entry in connection.entries:
                user_data = self._format_user_data(entry)
                if user_data:
                    users.append(user_data)
            
            # Manejar paginación si hay más resultados
            cookie = connection.result.get('controls', {}).get('1.2.840.113556.1.4.319', {}).get('value', {}).get('cookie')
            while cookie:
                connection.search(
                    search_base=ad_settings.AD_USER_BASE_DN,
                    search_filter=ad_settings.AD_USER_FILTER,
                    search_scope=SUBTREE,
                    attributes=[
                        ad_settings.AD_USERNAME_ATTRIBUTE,
                        ad_settings.AD_EMAIL_ATTRIBUTE,
                        ad_settings.AD_FULLNAME_ATTRIBUTE,
                        ad_settings.AD_DEPARTMENT_ATTRIBUTE,
                        'memberOf',
                        'userAccountControl',
                        'distinguishedName'
                    ],
                    paged_size=page_size,
                    paged_cookie=cookie
                )
                
                for entry in connection.entries:
                    user_data = self._format_user_data(entry)
                    if user_data:
                        users.append(user_data)
                
                cookie = connection.result.get('controls', {}).get('1.2.840.113556.1.4.319', {}).get('value', {}).get('cookie')
            
            connection.unbind()
            logger.info(f"Obtenidos {len(users)} usuarios de AD")
            return users
            
        except Exception as e:
            logger.error(f"Error obteniendo usuarios de AD: {str(e)}")
            return []
    
    def _format_user_data(self, entry) -> Optional[Dict]:
        """Formatea los datos del usuario desde AD"""
        try:
            # Verificar si la cuenta está activa (userAccountControl)
            account_control = entry.userAccountControl.value if hasattr(entry, 'userAccountControl') else 0
            is_disabled = bool(account_control & 0x2)  # ADS_UF_ACCOUNTDISABLE
            
            # Determinar si es administrador
            is_admin = self._is_user_admin(entry)
            
            user_data = {
                'dn': str(entry.distinguishedName),
                'username': str(getattr(entry, ad_settings.AD_USERNAME_ATTRIBUTE, '')),
                'email': str(getattr(entry, ad_settings.AD_EMAIL_ATTRIBUTE, '')),
                'fullname': str(getattr(entry, ad_settings.AD_FULLNAME_ATTRIBUTE, '')),
                'department': str(getattr(entry, ad_settings.AD_DEPARTMENT_ATTRIBUTE, '')),
                'is_active': not is_disabled,
                'is_admin': is_admin,
                'groups': [str(group) for group in (entry.memberOf.values if hasattr(entry, 'memberOf') else [])]
            }
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error formateando datos de usuario: {str(e)}")
            return None
    
    def _is_user_admin(self, entry) -> bool:
        """Determina si un usuario es administrador basado en sus grupos"""
        try:
            if not hasattr(entry, 'memberOf'):
                return False
            
            admin_groups = [group.strip() for group in ad_settings.AD_ADMIN_GROUPS.split(',')]
            user_groups = [str(group) for group in entry.memberOf.values]
            
            # Verificar si el usuario pertenece a algún grupo de admin
            for user_group in user_groups:
                for admin_group in admin_groups:
                    if admin_group.lower() in user_group.lower():
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando permisos de admin: {str(e)}")
            return False
    
    def test_connection(self) -> Dict:
        """Prueba la conexión con Active Directory"""
        try:
            connection = self._get_connection()
            
            # Realizar una búsqueda simple para probar
            connection.search(
                search_base=ad_settings.AD_BASE_DN,
                search_filter='(objectClass=*)',
                search_scope=SUBTREE,
                attributes=['distinguishedName'],
                size_limit=1
            )
            
            connection.unbind()
            
            return {
                'success': True,
                'message': 'Conexión exitosa con Active Directory',
                'server': ad_settings.AD_SERVER
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error conectando con Active Directory: {str(e)}',
                'server': ad_settings.AD_SERVER
            }

# Instancia global del servicio
ad_service = ActiveDirectoryService()