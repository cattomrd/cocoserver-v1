# Actualización para models/schemas.py

from pydantic import BaseModel
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