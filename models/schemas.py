# Actualización para models/schemas.py

from pydantic import BaseModel,Field
from datetime import datetime
from typing import List, Optional
from datetime import datetime

# Modelos Pydantic para la API
class VideoBase(BaseModel):
    title: str
    description: Optional[str] = None
    expiration_date: Optional[datetime] = None  # Nueva propiedad para fecha de expiración

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

class PlaylistResponse(PlaylistBase):
    id: int
    creation_date: datetime
    videos: List[VideoResponse] = []
    
    class Config:
        orm_mode = True

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

    class Config:
        from_attributes = True