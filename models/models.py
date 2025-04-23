# En tu archivo models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, Table, Float, func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from datetime import datetime
from typing import Optional, List
from .database import Base  # Asumiendo que tienes Base definido en database.py

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
    expiration_date = Column(DateTime, nullable=True)
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
    
    # Relación con PlaylistVideo
    playlist_videos = relationship("PlaylistVideo", back_populates="video", cascade="all, delete-orphan")
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

class DeviceBase(BaseModel):
    device_id: str
    name: str
    model: str
    ip_address_lan: Optional[str] = None
    ip_address_wifi: Optional[str] = None
    mac_address: str  # MAC principal (eth0)
    wlan0_mac: Optional[str] = None  # MAC WiFi (opcional)
    location: Optional[str] = None
    tienda: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    ip_address_lan: Optional[str] = None
    ip_address_wifi: Optional[str] = None
    location: Optional[str] = None
    tienda: Optional[str] = None
    is_active: Optional[bool] = None
    cpu_temp: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None

class DeviceStatus(BaseModel):
    device_id: str
    ip_address_lan: Optional[str] = None
    ip_address_wifi: Optional[str] = None
    cpu_temp: float = Field(..., description="CPU temperature in Celsius")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    videoloop_status: Optional[str] = Field(None, description="Status of videoloop service")
    kiosk_status: Optional[str] = Field(None, description="Status of kiosk service")
    wlan0_mac: Optional[str] = Field(None, description="MAC address of WiFi interface")

class ServiceStatus(BaseModel):
    name: str
    status: str
    active: bool
    enabled: bool
    runtime: Optional[str] = None
    description: Optional[str] = None

class ServiceAction(BaseModel):
    action: str = Field(..., description="Action to perform: start, stop, restart, status")
    service: str = Field(..., description="Service name: videoloop or kiosk")

class ServiceActionResponse(BaseModel):
    device_id: str
    action: str
    service: str
    success: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
