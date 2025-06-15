# utils/auth_enhanced.py - Servicio de autenticación con soporte AD

import logging
import os
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import hashlib

from models.models import User

logger = logging.getLogger(__name__)

class AuthenticationService:
    """Servicio de autenticación que soporta múltiples proveedores"""
    
    def __init__(self):
        self.session_store = {}  # En producción usar Redis o DB
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Autentica un usuario usando múltiples proveedores
        
        Returns:
            (success, user, message)
        """
        try:
            # Limpiar username
            username = username.strip().lower()
            
            logger.info(f"Intentando autenticar usuario: {username}")
            
            # 1. Primero intentar con usuario local existente
            local_user = db.query(User).filter(
                User.username == username,
                User.is_active == True
            ).first()
            
            if local_user and local_user.auth_provider == "local":
                # Usuario local - verificar contraseña
                if local_user.verify_password(password):
                    local_user.update_last_login()
                    db.commit()
                    logger.info(f"Autenticación local exitosa: {username}")
                    return True, local_user, "Autenticación local exitosa"
                else:
                    logger.warning(f"Contraseña incorrecta para usuario local: {username}")
                    return False, None, "Credenciales inválidas"
            
            # 2. Si no es usuario local, intentar con Active Directory
            if self._is_ad_enabled():
                logger.info(f"Intentando autenticación AD para: {username}")
                
                ad_success, ad_user_data = self._authenticate_with_ad(username, password)
                
                if ad_success and ad_user_data:
                    # Autenticación AD exitosa
                    logger.info(f"Autenticación AD exitosa: {username}")
                    
                    # Crear o actualizar usuario local desde AD
                    user = self._sync_user_from_ad(db, ad_user_data)
                    
                    if user:
                        user.update_last_login()
                        user.update_last_ad_sync()
                        db.commit()
                        return True, user, "Autenticación Active Directory exitosa"
                    else:
                        logger.error(f"Error sincronizando usuario AD: {username}")
                        return False, None, "Error sincronizando usuario"
                else:
                    logger.warning(f"Autenticación AD falló: {username}")
                    return False, None, "Credenciales de Active Directory inválidas"
            
            # 3. No se pudo autenticar con ningún proveedor
            logger.warning(f"Usuario no encontrado en ningún proveedor: {username}")
            return False, None, "Usuario no encontrado"
            
        except Exception as e:
            logger.error(f"Error en autenticación de {username}: {str(e)}")
            return False, None, "Error interno de autenticación"
    
    def _is_ad_enabled(self) -> bool:
        """Verifica si Active Directory está habilitado"""
        return os.getenv('AD_SYNC_ENABLED', 'false').lower() == 'true'
    
    def _authenticate_with_ad(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Autentica contra Active Directory"""
        try:
            # Intentar importar el servicio AD
            from services.ad_service import ad_service
            
            # Usar el servicio AD para autenticar
            success, user_data = ad_service.authenticate_user(username, password)
            
            if success and user_data:
                logger.info(f"AD authentication successful for: {username}")
                return True, user_data
            else:
                logger.warning(f"AD authentication failed for: {username}")
                return False, None
                
        except ImportError:
            logger.error("AD service not available")
            return False, None
        except Exception as e:
            logger.error(f"Error in AD authentication for {username}: {str(e)}")
            return False, None
    
    def _sync_user_from_ad(self, db: Session, ad_user_data: Dict) -> Optional[User]:
        """Sincroniza un usuario desde Active Directory"""
        try:
            username = ad_user_data.get('username')
            if not username:
                return None
            
            # Buscar usuario existente
            user = db.query(User).filter(User.username == username).first()
            
            # Determinar si es administrador basado en grupos
            is_admin = self._is_admin_user(ad_user_data)
            
            if user:
                # Actualizar usuario existente
                user.email = ad_user_data.get('email') or user.email
                user.fullname = ad_user_data.get('fullname') or user.fullname
                user.department = ad_user_data.get('department') or user.department
                user.is_admin = is_admin
                user.is_active = ad_user_data.get('is_enabled', True)
                user.auth_provider = 'ad'
                user.ad_dn = ad_user_data.get('dn')
                
                logger.info(f"Usuario AD actualizado: {username}")
            else:
                # Crear nuevo usuario
                user = User(
                    username=username,
                    email=ad_user_data.get('email'),
                    fullname=ad_user_data.get('fullname', username),
                    department=ad_user_data.get('department'),
                    is_admin=is_admin,
                    is_active=ad_user_data.get('is_enabled', True),
                    auth_provider='ad',
                    ad_dn=ad_user_data.get('dn'),
                    password_hash=None  # Usuarios AD no tienen contraseña local
                )
                
                db.add(user)
                logger.info(f"Nuevo usuario AD creado: {username}")
            
            db.commit()
            db.refresh(user)
            return user
            
        except Exception as e:
            logger.error(f"Error sincronizando usuario AD: {str(e)}")
            db.rollback()
            return None
    
    def _is_admin_user(self, ad_user_data: Dict) -> bool:
        """Determina si un usuario de AD debe ser administrador"""
        try:
            admin_groups = os.getenv('AD_ADMIN_GROUPS', 'Domain Admins,Administrators').split(',')
            user_groups = ad_user_data.get('groups', [])
            
            for group in user_groups:
                group_name = group.split(',')[0].replace('CN=', '').strip()
                if group_name in admin_groups:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def create_access_token(self, user: User) -> Dict[str, Any]:
        """Crea un token de acceso para el usuario"""
        # Generar session ID
        session_id = secrets.token_urlsafe(32)
        
        # Datos del token
        token_data = {
            "session_id": session_id,
            "user_id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "auth_provider": user.auth_provider,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        
        # Guardar en store (en producción usar Redis)
        self.session_store[session_id] = token_data
        
        return {
            "access_token": session_id,
            "token_type": "bearer",
            "expires_in": 86400,  # 24 horas
            "user": {
                "id": user.id,
                "username": user.username,
                "fullname": user.fullname,
                "email": user.email,
                "is_admin": user.is_admin,
                "auth_provider": user.auth_provider
            }
        }
    
    def verify_session(self, session_id: str) -> Optional[Dict]:
        """Verifica un session ID"""
        if not session_id:
            return None
            
        session_data = self.session_store.get(session_id)
        if not session_data:
            return None
        
        # Verificar expiración
        if datetime.now() > session_data['expires_at']:
            del self.session_store[session_id]
            return None
        
        return session_data
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoca un session ID"""
        if session_id in self.session_store:
            del self.session_store[session_id]
            return True
        return False

# Instancia global del servicio
auth_service = AuthenticationService()