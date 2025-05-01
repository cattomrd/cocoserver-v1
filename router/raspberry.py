# Update to router/raspberry.py to ensure compatibility with authentication system

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from models.database import get_db
from models.models import Playlist, Video, Device, DevicePlaylist


# Configure logging
logger = logging.getLogger('server')

router = APIRouter(
    prefix="/api/raspberry",
    tags=["raspberry"]
)

@router.get("/playlists/active")
def get_active_playlists_for_raspberry(
    device_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns all active playlists.
    If device_id is provided, returns only playlists assigned to that device.
    This is a public endpoint accessible to Raspberry Pi devices without authentication.
    """
    now = datetime.now()
    
    # Build base query for active playlists
    query = db.query(Playlist).filter(
        Playlist.is_active == True,
        (Playlist.expiration_date == None) | (Playlist.expiration_date > now)
    )
    
    # If device_id is provided, filter by playlists assigned to that device
    if device_id:
        # Check if device exists
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if device is None:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        
        # Update last_seen timestamp
        device.last_seen = datetime.now()
        db.commit()
        
        # Filter playlists assigned to the device
        query = query.join(
            DevicePlaylist,
            DevicePlaylist.playlist_id == Playlist.id
        ).filter(DevicePlaylist.device_id == device_id)
    
    # Execute the query
    active_playlists = query.all()
    
    result = []
    for playlist in active_playlists:
        # Filter videos that haven't expired
        active_videos = [
            video for video in playlist.videos 
            if not video.expiration_date or video.expiration_date > now
        ]
        
        # Only include playlists with at least one active video
        if active_videos:
            playlist_data = {
                "id": playlist.id,
                "title": playlist.title,
                "description": playlist.description,
                "expiration_date": playlist.expiration_date.isoformat() if playlist.expiration_date else None,
                "videos": [
                    {
                        "id": video.id,
                        "title": video.title,
                        "file_path": f"/api/videos/{video.id}/download",
                        "duration": video.duration,
                        "expiration_date": video.expiration_date.isoformat() if video.expiration_date else None
                    }
                    for video in active_videos
                ]
            }
            result.append(playlist_data)
    
    return result

@router.get("/playlists/active/{device_id}")
def get_active_playlists_for_device(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns the active playlists assigned to a specific device.
    This endpoint is for direct access from the client.
    """
    try:
        # Check if device exists and update last_seen
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if device is None:
            logger.error(f"Device not found: {device_id}")
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        
        # Update last_seen timestamp
        device.last_seen = datetime.now()
        db.commit()
        
        logger.info(f"Active playlists request for device {device_id}")
        
        # Use the existing function but explicitly pass the device_id
        return get_active_playlists_for_raspberry(device_id=device_id, db=db)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlists for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Keep the rest of your code as is...