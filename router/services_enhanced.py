# router/services_enhanced.py
import tempfile
from fastapi import APIRouter, Request, Depends, HTTPException, Response, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
import requests
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, Union, List
import httpx
import asyncio
import os
import subprocess
import paramiko
import logging
from datetime import datetime

from utils import ssh_helper
from models import models
from models.database import SessionLocal, get_db

router = APIRouter(
    prefix="/services",
    tags=["services"]
)

logger = logging.getLogger(__name__)


import subprocess
import requests
from fastapi import HTTPException, Depends, Response
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

@router.get("/devices/{device_id}/screenshot")
async def get_device_screenshot(device_id: str, db: Session = Depends(get_db)):
    """
    Obtiene una captura de pantalla del dispositivo remoto.
    Consume el endpoint API del cliente para capturar la pantalla.
    """
    try:
        # Buscar el dispositivo en la base de datos
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if device is None:
            logger.error(f"Dispositivo no encontrado: {device_id}")
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        
        # Verificar si el dispositivo está activo
        if not device.is_active:
            logger.error(f"El dispositivo {device_id} no está activo")
            raise HTTPException(status_code=400, detail="El dispositivo no está activo")
        
        # Función para hacer ping a una IP
        def ping_ip(ip_address):
            """Hace ping a una IP y retorna True si responde"""
            try:
                # Para Windows usar -n, para Linux/Mac usar -c
                import platform
                param = "-n" if platform.system().lower() == "windows" else "-c"
                
                result = subprocess.run(
                    ['ping', param, '1', ip_address], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                return False
        
        # Determinar la IP a usar (preferir WiFi, fallback a LAN)
        device_ip = None
        
        # Primero intentar con WiFi
        if device.ip_address_wifi:
            logger.info(f"Probando conectividad WiFi: {device.ip_address_wifi}")
            if ping_ip(device.ip_address_wifi):
                device_ip = device.ip_address_wifi
                logger.info(f"Dispositivo accesible via WiFi: {device_ip}")
        
        # Si WiFi no responde, intentar con LAN
        if not device_ip and device.ip_address_lan:
            logger.info(f"Probando conectividad LAN: {device.ip_address_lan}")
            if ping_ip(device.ip_address_lan):
                device_ip = device.ip_address_lan
                logger.info(f"Dispositivo accesible via LAN: {device_ip}")
        
        # Si ninguna IP responde
        if not device_ip:
            logger.error(f"El dispositivo {device_id} no responde a ping en ninguna IP")
            raise HTTPException(
                status_code=400, 
                detail="El dispositivo no está accesible en la red"
            )
        
        # URL del endpoint de captura de pantalla en el cliente
        screenshot_url = f"http://{device_ip}:8000/api/screenshot/"
        
        logger.info(f"Solicitando captura de pantalla desde {screenshot_url}")
        
        # Realizar la solicitud al cliente
        try:
            # Configurar timeout para evitar esperas largas
            response = requests.get(screenshot_url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Error al obtener captura desde el cliente: {response.status_code}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error al obtener captura desde el cliente: {response.status_code}"
                )
                
            # Obtener el contenido de la imagen
            image_content = response.content
            
            # Método directo: devolver la imagen directamente
            return Response(
                content=image_content,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"inline; filename=screenshot-{device.name}.png"
                }
            )
            
        except requests.RequestException as e:
            logger.error(f"Error de conexión con el cliente: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error al conectar con el dispositivo: {str(e)}"
            )
            
    except HTTPException:
        # Re-lanzar excepciones HTTPException
        raise
    except Exception as e:
        logger.exception(f"Error al procesar la solicitud de captura: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/devices/{device_id}/screenshot/file")
async def get_device_screenshot_as_file(device_id: str, db: Session = Depends(get_db)):
    """
    Obtiene una captura de pantalla del dispositivo remoto y la devuelve como un archivo descargable.
    Este método utiliza archivos temporales.
    """
    try:
        # Buscar el dispositivo en la base de datos
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if device is None:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
        
        # Verificar si el dispositivo está activo
        if not device.is_active:
            raise HTTPException(status_code=400, detail="El dispositivo no está activo")
        
        # Obtener dirección IP del dispositivo
        device_ip = device.ip_address_lan or device.ip_address_wifi
        if not device_ip:
            raise HTTPException(
                status_code=400, 
                detail="No se encontró una dirección IP válida para el dispositivo"
            )
        
        # URL del endpoint de captura de pantalla en el cliente
        screenshot_url = f"http://{device_ip}:8000/api/screenshot/"
        
        # Realizar la solicitud al cliente
        try:
            response = requests.get(screenshot_url, timeout=10)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Error al obtener captura desde el cliente: {response.status_code}"
                )
            
            # Crear un archivo temporal para la imagen
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            # Función para eliminar el archivo temporal después de enviarlo
            def cleanup():
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            # Devolver el archivo
            return FileResponse(
                path=temp_path,
                filename=f"screenshot-{device.name}.png",
                media_type="image/png",
                background=BackgroundTasks(cleanup)  # Usar la función de limpieza
            )
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error al conectar con el dispositivo: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error al procesar la solicitud de captura: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")