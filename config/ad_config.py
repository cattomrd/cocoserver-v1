# config/ad_config.py - Configuración para Active Directory (versión simplificada)

import os
from typing import Optional

class ADSettings:
    """Configuración de Active Directory"""
    
    def __init__(self):
        # Configuración del servidor AD
        self.AD_SERVER = os.getenv("AD_SERVER", "ldap://tu-servidor-ad.tudominio.com")
        self.AD_PORT = int(os.getenv("AD_PORT", "389"))
        self.AD_USE_SSL = os.getenv("AD_USE_SSL", "false").lower() == "true"
        self.AD_SSL_PORT = int(os.getenv("AD_SSL_PORT", "636"))
        
        # Credenciales para búsqueda en AD
        self.AD_BIND_DN = os.getenv("AD_BIND_DN", "CN=ServiceAccount,OU=Service Accounts,DC=tudominio,DC=com")
        self.AD_BIND_PASSWORD = os.getenv("AD_BIND_PASSWORD", "tu_password_servicio")
        
        # Base DN para búsquedas
        self.AD_BASE_DN = os.getenv("AD_BASE_DN", "DC=tudominio,DC=com")
        self.AD_USER_BASE_DN = os.getenv("AD_USER_BASE_DN", "OU=Users,DC=tudominio,DC=com")
        self.AD_GROUP_BASE_DN = os.getenv("AD_GROUP_BASE_DN", "OU=Groups,DC=tudominio,DC=com")
        
        # Configuración de campos de usuario
        self.AD_USERNAME_ATTRIBUTE = os.getenv("AD_USERNAME_ATTRIBUTE", "sAMAccountName")
        self.AD_EMAIL_ATTRIBUTE = os.getenv("AD_EMAIL_ATTRIBUTE", "mail")
        self.AD_FULLNAME_ATTRIBUTE = os.getenv("AD_FULLNAME_ATTRIBUTE", "displayName")
        self.AD_DEPARTMENT_ATTRIBUTE = os.getenv("AD_DEPARTMENT_ATTRIBUTE", "department")
        
        # Grupos de administrador
        self.AD_ADMIN_GROUPS = os.getenv("AD_ADMIN_GROUPS", "Domain Admins,System Administrators")
        
        # Configuración de sincronización
        self.AD_SYNC_ENABLED = os.getenv("AD_SYNC_ENABLED", "true").lower() == "true"
        self.AD_AUTO_CREATE_USERS = os.getenv("AD_AUTO_CREATE_USERS", "true").lower() == "true"
        self.AD_UPDATE_USER_INFO = os.getenv("AD_UPDATE_USER_INFO", "true").lower() == "true"
        
        # Filtros de búsqueda
        self.AD_USER_FILTER = os.getenv("AD_USER_FILTER", "(&(objectClass=user)(objectCategory=person))")
        self.AD_GROUP_FILTER = os.getenv("AD_GROUP_FILTER", "(objectClass=group)")

# Instancia global de configuración
ad_settings = ADSettings()