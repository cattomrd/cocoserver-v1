# models/schemas.py (reemplaza COMPLETAMENTE el archivo actual si ya existe)

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, ForwardRef
import warnings
warnings.filterwarnings("ignore", message="Valid config keys have changed in V2")

# Esquemas para Video
class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    expiration_date: Optional[datetime] = None

class VideoCreate(VideoBase):
    pass

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    expiration_date: Optional[datetime] = None

class VideoResponse(VideoBase):
    id: int
    file_path: str
    file_size: Optional[int] = None
    duration: Optional[int] = None
    upload_date: datetime
    
    class Config:
        orm_mode = True

# Esquemas para Playlist
class PlaylistBase(BaseModel):
    title: str
    description: Optional[str] = None
    expiration_date: Optional[datetime] = None
    is_active: Optional[bool] = True

class PlaylistCreate(PlaylistBase):
    pass

class PlaylistUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    expiration_date: Optional[datetime] = None
    is_active: Optional[bool] = None

# Forward refs para resolver referencias circulares
DeviceInfoRef = ForwardRef('DeviceInfo')

class PlaylistResponse(PlaylistBase):
    id: int
    creation_date: datetime
    videos: List[VideoResponse] = []
    devices: List[DeviceInfoRef] = []
    
    class Config:
        orm_mode = True

# Esquemas para Device
class DeviceBase(BaseModel):
    device_id: str
    name: str
    model: str
    ip_address_lan: Optional[str] = None
    ip_address_wifi: Optional[str] = None
    mac_address: str
    wlan0_mac: Optional[str] = None
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

# Forward refs para resolver referencias circulares
PlaylistInfoRef = ForwardRef('PlaylistInfo')

class Device(DeviceBase):
    id: int
    is_active: bool
    cpu_temp: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    videoloop_status: Optional[str] = None
    kiosk_status: Optional[str] = None
    last_seen: datetime
    registered_at: datetime
    playlists: List[PlaylistInfoRef] = []

    class Config:
        orm_mode = True

# Esquemas simplificados para evitar recursión infinita
class DeviceInfo(BaseModel):
    device_id: str
    name: str
    is_active: bool
    location: Optional[str] = None
    tienda: Optional[str] = None

    class Config:
        orm_mode = True

class PlaylistInfo(BaseModel):
    id: int
    title: str
    is_active: bool
    expiration_date: Optional[datetime] = None

    class Config:
        orm_mode = True

# Esquemas para DevicePlaylist
class DevicePlaylistBase(BaseModel):
    device_id: str
    playlist_id: int

class DevicePlaylistCreate(DevicePlaylistBase):
    pass

class DevicePlaylistResponse(DevicePlaylistBase):
    id: int
    assigned_at: datetime

    class Config:
        orm_mode = True

# Estado del dispositivo
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

# Servicio
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

# Resolver referencias circulares
PlaylistResponse.update_forward_refs()
Device.update_forward_refs()

# Agregar esto al archivo models/schemas.py

from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from datetime import datetime

# Esquema base para usuarios
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None

# Esquema para creación de usuarios (registro)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

# Esquema para actualización de usuarios
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

# Esquema para cambiar contraseña
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Las contraseñas no coinciden')
        return v

# Esquema para datos de usuario en respuestas
class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True

# Esquema para solicitud de token (login)
class TokenRequest(BaseModel):
    username: str
    password: str

# Esquema para respuesta con token
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse
