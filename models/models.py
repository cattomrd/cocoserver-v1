# En tu archivo models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint, Table
from sqlalchemy.orm import relationship
from datetime import datetime
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