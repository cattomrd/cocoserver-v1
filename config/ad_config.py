# config/ad_config.py - Configuración para Active Directory

import os
from typing import Optional
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()
class ADSettings(BaseSettings):
    """Configuración de Active Directory"""
    
    # Configuración del servidor AD
    AD_SERVER: str = os.getenv("AD_SERVER", "ldap://tu-servidor-ad.tudominio.com")
    AD_PORT: int = int(os.getenv("AD_PORT", "389"))
    AD_USE_SSL: bool = os.getenv("AD_USE_SSL", "false").lower() == "true"
    AD_SSL_PORT: int = int(os.getenv("AD_SSL_PORT", "636"))
    
    # Credenciales para búsqueda en AD
    AD_BIND_DN: str = os.getenv("AD_BIND_DN", "CN=ServiceAccount,OU=Service Accounts,DC=tudominio,DC=com")
    AD_BIND_PASSWORD: str = os.getenv("AD_BIND_PASSWORD", "tu_password_servicio")
    
    # Base DN para búsquedas
    AD_BASE_DN: str = os.getenv("AD_BASE_DN", "DC=tudominio,DC=com")
    AD_USER_BASE_DN: str = os.getenv("AD_USER_BASE_DN", "OU=Users,DC=tudominio,DC=com")
    AD_GROUP_BASE_DN: str = os.getenv("AD_GROUP_BASE_DN", "OU=Groups,DC=tudominio,DC=com")
    
    # Configuración de campos de usuario
    AD_USERNAME_ATTRIBUTE: str = os.getenv("AD_USERNAME_ATTRIBUTE", "sAMAccountName")
    AD_EMAIL_ATTRIBUTE: str = os.getenv("AD_EMAIL_ATTRIBUTE", "mail")
    AD_FULLNAME_ATTRIBUTE: str = os.getenv("AD_FULLNAME_ATTRIBUTE", "displayName")
    AD_DEPARTMENT_ATTRIBUTE: str = os.getenv("AD_DEPARTMENT_ATTRIBUTE", "department")
    
    # Grupos de administrador
    AD_ADMIN_GROUPS: str = os.getenv("AD_ADMIN_GROUPS", "Domain Admins,System Administrators")
    
    # Configuración de sincronización
    AD_SYNC_ENABLED: bool = os.getenv("AD_SYNC_ENABLED", "true").lower() == "true"
    AD_AUTO_CREATE_USERS: bool = os.getenv("AD_AUTO_CREATE_USERS", "true").lower() == "true"
    AD_UPDATE_USER_INFO: bool = os.getenv("AD_UPDATE_USER_INFO", "true").lower() == "true"
    
    # Filtros de búsqueda
    AD_USER_FILTER: str = os.getenv("AD_USER_FILTER", "(&(objectClass=user)(objectCategory=person))")
    AD_GROUP_FILTER: str = os.getenv("AD_GROUP_FILTER", "(objectClass=group)")
    
    class Config:
        env_file = ".env"

# Instancia global de configuración
ad_settings = ADSettings()