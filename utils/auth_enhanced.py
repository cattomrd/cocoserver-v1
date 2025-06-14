# utils/auth_enhanced.py - Servicio de autenticación mejorado con soporte AD

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import time

from models.database import get_db
from models.models import User, AuthProvider, ADSyncLog
from services.ad_service import ad_service
from config.ad_config import ad_settings

logger = logging.getLogger(__name__)

# Configuración JWT
SECRET_KEY = "your-secret-key-here"  # Cambiar por una clave segura
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas

security = HTTPBearer()

class AuthService:
    """Servicio de autenticación con soporte para múltiples proveedores"""
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Autentica un usuario contra múltiples proveedores
        
        Returns:
            Tuple[bool, Optional[User], str]: (éxito, usuario, mensaje)
        """
        try:
            # Primero intentar autenticación local
            local_user = User.authenticate_local(db, username, password)
            if local_user:
                logger.info(f"Autenticación local exitosa para: {username}")
                return True, local_user, "Autenticación local exitosa"
            
            # Si falla local y AD está habilitado, intentar AD
            if ad_settings.AD_SYNC_ENABLED:
                success, ad_user_data = ad_service.authenticate_user(username, password)
                
                if success and ad_user_data:
                    # Verificar si el usuario ya existe en la BD local
                    existing_user = User.get_by_username(db, username)
                    
                    if existing_user:
                        # Usuario existe, actualizar información desde AD si está configurado
                        if (existing_user.auth_provider == AuthProvider.ACTIVE_DIRECTORY.value and 
                            ad_settings.AD_UPDATE_USER_INFO):
                            existing_user.update_from_ad(ad_user_data)
                            db.commit()
                        
                        existing_user.update_last_login()
                        db.commit()
                        
                        logger.info(f"Autenticación AD exitosa para usuario existente: {username}")
                        return True, existing_user, "Autenticación AD exitosa"
                    
                    elif ad_settings.AD_AUTO_CREATE_USERS:
                        # Crear nuevo usuario desde AD
                        new_user = User.create_from_ad(db, ad_user_data)
                        new_user.update_last_login()
                        db.commit()
                        
                        logger.info(f"Usuario creado desde AD: {username}")
                        return True, new_user, "Usuario creado desde AD"
                    
                    else:
                        logger.warning(f"Usuario autenticado en AD pero no existe localmente: {username}")
                        return False, None, "Usuario no autorizado en el sistema local"
                
                else:
                    logger.warning(f"Falló autenticación AD para: {username}")
            
            logger.warning(f"Falló autenticación para: {username}")
            return False, None, "Credenciales inválidas"
            
        except Exception as e:
            logger.error(f"Error en autenticación de {username}: {str(e)}")
            return False, None, "Error interno de autenticación"
    
    def create_access_token(self, user: User) -> Dict:
        """Crea un token de acceso JWT"""
        try:
            # Datos del token
            token_data = {
                "sub": user.username,
                "user_id": user.id,
                "is_admin": user.is_admin,
                "auth_provider": user.auth_provider,
                "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
                "iat": datetime.utcnow()
            }
            
            # Crear token
            access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": user.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error creando token para {user.username}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando token de acceso"
            )
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Decodifica y valida un token JWT"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Verificar expiración
            if datetime.fromtimestamp(payload.get("exp", 0)) < datetime.utcnow():
                return None
            
            return payload
            
        except JWTError:
            return None
        except Exception as e:
            logger.error(f"Error decodificando token: {str(e)}")
            return None
    
    def get_current_user(self, db: Session, token: str) -> Optional[User]:
        """Obtiene el usuario actual desde el token"""
        try:
            payload = self.decode_token(token)
            if not payload:
                return None
            
            username = payload.get("sub")
            if not username:
                return None
            
            user = User.get_by_username(db, username)
            if not user or not user.is_active:
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"Error obteniendo usuario actual: {str(e)}")
            return None
    
    def sync_users_from_ad(self, db: Session) -> Dict:
        """Sincroniza usuarios desde Active Directory"""
        start_time = time.time()
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'messages': []
        }
        
        try:
            if not ad_settings.AD_SYNC_ENABLED:
                return {'success': False, 'message': 'Sincronización AD deshabilitada'}
            
            # Obtener usuarios de AD
            logger.info("Iniciando sincronización de usuarios desde AD...")
            ad_users = ad_service.get_all_users()
            
            if not ad_users:
                message = "No se obtuvieron usuarios de AD"
                logger.warning(message)
                return {'success': False, 'message': message}
            
            stats['processed'] = len(ad_users)
            logger.info(f"Procesando {len(ad_users)} usuarios de AD...")
            
            for ad_user in ad_users:
                try:
                    username = ad_user.get('username')
                    if not username:
                        stats['errors'] += 1
                        continue
                    
                    # Verificar si el usuario ya existe
                    existing_user = User.get_by_username(db, username)
                    
                    if existing_user:
                        # Actualizar usuario existente si es de AD
                        if existing_user.auth_provider == AuthProvider.ACTIVE_DIRECTORY.value:
                            existing_user.update_from_ad(ad_user)
                            stats['updated'] += 1
                            logger.debug(f"Usuario actualizado: {username}")
                    else:
                        # Crear nuevo usuario desde AD
                        if ad_settings.AD_AUTO_CREATE_USERS:
                            User.create_from_ad(db, ad_user)
                            stats['created'] += 1
                            logger.debug(f"Usuario creado: {username}")
                
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error procesando usuario {ad_user.get('username', 'unknown')}: {str(e)}")
            
            # Confirmar cambios
            db.commit()
            
            duration = time.time() - start_time
            message = f"Sincronización completada: {stats['created']} creados, {stats['updated']} actualizados, {stats['errors']} errores"
            
            # Crear log de sincronización
            ADSyncLog.create_log(
                db=db,
                sync_type='full',
                status='success' if stats['errors'] == 0 else 'partial',
                message=message,
                users_processed=stats['processed'],
                users_created=stats['created'],
                users_updated=stats['updated'],
                users_errors=stats['errors'],
                duration_seconds=duration
            )
            
            logger.info(message)
            return {
                'success': True,
                'message': message,
                'stats': stats,
                'duration': duration
            }
            
        except Exception as e:
            db.rollback()
            duration = time.time() - start_time
            error_message = f"Error en sincronización AD: {str(e)}"
            
            # Crear log de error
            ADSyncLog.create_log(
                db=db,
                sync_type='full',
                status='error',
                message=error_message,
                users_processed=stats['processed'],
                users_created=stats['created'],
                users_updated=stats['updated'],
                users_errors=stats['errors'],
                duration_seconds=duration
            )
            
            logger.error(error_message)
            return {
                'success': False,
                'message': error_message,
                'stats': stats,
                'duration': duration
            }

# Instancia global del servicio
auth_service = AuthService()

# Dependencias de FastAPI
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), 
                    db: Session = Depends(get_db)) -> User:
    """Dependencia para obtener el usuario actual autenticado"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_current_user(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def admin_required(current_user: User = Depends(get_current_user)) -> User:
    """Dependencia que requiere permisos de administrador"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos de administrador requeridos"
        )
    return current_user

def active_user_required(current_user: User = Depends(get_current_user)) -> User:
    """Dependencia que requiere usuario activo"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    return current_user
