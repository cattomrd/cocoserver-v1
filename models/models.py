# models/models.py (reemplaza COMPLETAMENTE el archivo actual)

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, Float, func, or_
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from typing import Optional
from datetime import datetime
from enum import Enum
from .database import Base
from passlib.context import CryptContext

# Tabla de relación entre Playlist y Video (modelo asociativo)
class PlaylistVideo(Base):
    __tablename__ = "playlist_videos"
    
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, default=0)  # Campo para mantener el orden
    created_at = Column(DateTime, default=datetime.now)
    
    # Relaciones
    playlist = relationship("Playlist", back_populates="playlist_videos")
    video = relationship("Video", back_populates="playlist_videos")
    
    # Restricción para asegurar posiciones únicas dentro de una playlist
    __table_args__ = (
        UniqueConstraint('playlist_id', 'position', name='uix_position_playlist'),
    )


class Playlist(Base):
    __tablename__ = "playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    creation_date = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    start_date = Column(DateTime, nullable=True)  # Fecha de inicio de la playlist
    expiration_date = Column(DateTime, nullable=True)  # Fecha de fin de la playlist
    is_active = Column(Boolean, default=True)
    
    # Relación con PlaylistVideo
    playlist_videos = relationship("PlaylistVideo", back_populates="playlist", cascade="all, delete-orphan")
    
    # Relación con Video a través de PlaylistVideo
    videos = relationship(
        "Video", 
        secondary="playlist_videos",
        viewonly=True,
        backref="playlists"
    )
    
    # Relación con DevicePlaylist
    device_playlists = relationship("DevicePlaylist", back_populates="playlist", cascade="all, delete-orphan")
    
    # Relación con Device a través de DevicePlaylist
    devices = relationship(
        "Device", 
        secondary="device_playlists",
        viewonly=True
    )
    
    @property
    def is_currently_active(self):
        """
        Verifica si la playlist está activa según las fechas de inicio y fin
        """
        if not self.is_active:
            return False
            
        now = datetime.now()
        
        # Verificar fecha de inicio
        if self.start_date and now < self.start_date:
            return False
        
        # Verificar fecha de expiración
        if self.expiration_date and now > self.expiration_date:
            return False
            
        return True

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    upload_date = Column(DateTime, default=datetime.now)
    duration = Column(Integer, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    
    # Relación con PlaylistVideo
    playlist_videos = relationship("PlaylistVideo", back_populates="video", cascade="all, delete-orphan")
    
    @property
    def formatted_duration(self):
        """Devuelve la duración formateada como HH:MM:SS"""
        if self.duration is None:
            return "Desconocida"
        
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    @property
    def formatted_file_size(self):
        """Devuelve el tamaño de archivo en un formato legible"""
        if self.file_size is None:
            return "Desconocido"
        
        # Convertir bytes a una unidad legible
        size_bytes = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024

class DevicePlaylist(Base):
    __tablename__ = "device_playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.now)
    
    # Relaciones
    device = relationship("Device", back_populates="device_playlists")
    playlist = relationship("Playlist", back_populates="device_playlists")
    
    # Restricción para asegurar combinaciones únicas de dispositivo-playlist
    __table_args__ = (
        UniqueConstraint('device_id', 'playlist_id', name='uix_device_playlist'),
    )

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True)
    name = Column(String)
    model = Column(String)
    ip_address_lan = Column(String)
    ip_address_wifi = Column(String)
    mac_address = Column(String, unique=True)  # MAC principal (eth0)
    wlan0_mac = Column(String, nullable=True)  # MAC WiFi (opcional)
    location = Column(String, nullable=True)
    tienda = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    cpu_temp = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    videoloop_status = Column(String, nullable=True)
    kiosk_status = Column(String, nullable=True)
    # Nuevos campos para control de autoarranque
    videoloop_enabled = Column(Boolean, default=True)  # Indica si el servicio está habilitado para iniciar con el sistema
    kiosk_enabled = Column(Boolean, default=False)  # Indica si el servicio está habilitado para iniciar con el sistema
    last_seen = Column(DateTime, default=func.now(), onupdate=func.now())
    registered_at = Column(DateTime, default=func.now())
    service_logs = Column(String, nullable=True)
    
    # Relación con DevicePlaylist
    device_playlists = relationship("DevicePlaylist", back_populates="device", cascade="all, delete-orphan")
    
    # Relación con Playlist a través de DevicePlaylist
    playlists = relationship(
        "Playlist", 
        secondary="device_playlists",
        viewonly=True
    )

# Scripts de migración para añadir nuevos campos
migration_scripts = {
    'sqlite': '''
-- Script de migración para SQLite
ALTER TABLE devices ADD COLUMN videoloop_enabled BOOLEAN DEFAULT 1;
ALTER TABLE devices ADD COLUMN kiosk_enabled BOOLEAN DEFAULT 0;
''',
    'postgresql': '''
-- Script de migración para PostgreSQL
ALTER TABLE devices ADD COLUMN IF NOT EXISTS videoloop_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS kiosk_enabled BOOLEAN DEFAULT FALSE;
'''
}


# Código para aplicar la migración
def apply_migration(engine):
    """
    Aplica la migración para añadir los campos de habilitación de servicios
    
    Args:
        engine: Instancia del motor SQLAlchemy
    """
    from sqlalchemy import inspect
    
    # Detectar el dialecto de la base de datos
    dialect = engine.dialect.name
    
    # Obtener el script de migración adecuado
    if dialect not in migration_scripts:
        raise ValueError(f"No hay script de migración para el dialecto {dialect}")
    
    script = migration_scripts[dialect]
    
    # Verificar si los campos ya existen
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('devices')]
    
    if 'videoloop_enabled' in existing_columns and 'kiosk_enabled' in existing_columns:
        print("Los campos de habilitación de servicios ya existen. No se requiere migración.")
        return
    
    # Aplicar el script de migración
    with engine.begin() as conn:
        conn.execute(script)
    
    print("Migración aplicada correctamente.")


# Configuración de encriptación de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthProvider(str, Enum):
    """Proveedores de autenticación"""
    LOCAL = "local"
    ACTIVE_DIRECTORY = "ad"
    LDAP = "ldap"

# Actualización del modelo User para soporte de Active Directory
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(128), nullable=True)  # NULL para usuarios AD
    fullname = Column(String(100))
    department = Column(String(100), nullable=True)  # Nuevo campo
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False, index=True)
    
    # Campos para Active Directory
    auth_provider = Column(String(20), default="local", index=True)  # "local" o "ad"
    ad_dn = Column(Text, nullable=True)  # Distinguished Name en AD
    last_ad_sync = Column(DateTime, nullable=True)  # Última sincronización con AD
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', auth_provider='{self.auth_provider}')>"
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
        
    @password.setter
    def password(self, password):
        if password:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            self.password_hash = pwd_context.hash(password)
        else:
            self.password_hash = None
        
    def verify_password(self, password: str) -> bool:
        """Verifica la contraseña para usuarios locales"""
        if not self.password_hash or self.auth_provider != "local":
            return False
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.password_hash)
    
    def update_last_login(self):
        """Actualiza la fecha del último login"""
        self.last_login = datetime.now()
    
    def update_last_ad_sync(self):
        """Actualiza la fecha de la última sincronización con AD"""
        self.last_ad_sync = datetime.now()
    
    def to_dict(self):
        """Convierte el usuario a diccionario"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "fullname": self.fullname,
            "department": self.department,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "last_ad_sync": self.last_ad_sync.isoformat() if self.last_ad_sync else None
        }
    
    @classmethod
    def create_user(cls, db, username, email=None, password=None, fullname=None, 
                   department=None, is_admin=False, auth_provider="local", ad_dn=None):
        """Crea un nuevo usuario"""
        user = cls(
            username=username,
            email=email,
            fullname=fullname,
            department=department,
            is_admin=is_admin,
            auth_provider=auth_provider,
            ad_dn=ad_dn
        )
        
        if password and auth_provider == "local":
            user.password = password
        else:
            user.password_hash = None
            
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

# Clase para logs de sincronización con AD
class ADSyncLog(Base):
    __tablename__ = "ad_sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(String(50), nullable=False)  # 'full', 'user', 'auth'
    status = Column(String(20), nullable=False)     # 'success', 'error', 'partial'
    message = Column(Text)
    users_processed = Column(Integer, default=0)
    users_created = Column(Integer, default=0)
    users_updated = Column(Integer, default=0)
    users_errors = Column(Integer, default=0)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    
    @classmethod
    def create_log(cls, db, sync_type: str, status: str, message: str = None,
                    users_processed: int = 0, users_created: int = 0, 
                    users_updated: int = 0, users_errors: int = 0,
                    duration_seconds: float = 0):
        """Crear un log de sincronización"""
        log = cls(
            sync_type=sync_type,
            status=status,
            message=message,
            users_processed=users_processed,
            users_created=users_created,
            users_updated=users_updated,
            users_errors=users_errors,
            duration_seconds=duration_seconds
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        return log