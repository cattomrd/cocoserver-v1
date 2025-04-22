#!/usr/bin/env python3
# Cliente para sincronización de videos en Raspberry Pi con reinicio de servicio

import os
import sys
import json
import time
import requests
import traceback
import argparse
import logging
import subprocess
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("raspberry_downloader.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RaspberryDownloader")

class VideoDownloaderClient:
    def __init__(self, server_url, download_path, check_interval=30, service_name="videoloop.service"):
        """Inicializa el cliente de descarga"""
        self.server_url = server_url
        self.download_path = download_path
        self.check_interval = check_interval
        self.playlists_path = os.path.join(download_path, "playlists")
        self.service_name = service_name
        
        # Crear directorios si no existen
        os.makedirs(self.playlists_path, exist_ok=True)
        
        # Estado del cliente
        self.active_playlists = {}
        self.last_update = None
        self.changes_detected = False
    
    def start(self):
        """Inicia el cliente de sincronización"""
        logger.info(f"Iniciando cliente sincronizador para {self.server_url}")
        logger.info(f"Directorio de descarga: {self.download_path}")
        logger.info(f"Intervalo de verificación: {self.check_interval} minutos")
        logger.info(f"Servicio a reiniciar: {self.service_name}")
        
        # Cargar estado previo si existe
        self.load_state()
        
        # Verificar inmediatamente al inicio
        self.check_for_updates()
        
        # Si se detectaron cambios en la verificación inicial, reiniciar servicio
        if self.changes_detected:
            self.restart_videoloop_service()
            self.changes_detected = False
        
        # Bucle principal de sincronización
        try:
            while True:
                # Esperar antes de la próxima verificación
                logger.info(f"Esperando {self.check_interval} minutos hasta la próxima verificación...")
                time.sleep(self.check_interval * 60)
                
                # Verificar actualizaciones
                self.check_for_updates()
                
                # Si se detectaron cambios, reiniciar el servicio de reproducción
                if self.changes_detected:
                    self.restart_videoloop_service()
                    self.changes_detected = False
        
        except KeyboardInterrupt:
            logger.info("Cliente detenido por el usuario")
    
    def load_state(self):
        """Carga el estado previo si existe"""
        state_file = os.path.join(self.download_path, "client_state.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
                    self.active_playlists = state.get("active_playlists", {})
                    self.last_update = state.get("last_update")
                logger.info(f"Estado cargado: {len(self.active_playlists)} playlists activas")
            except Exception as e:
                logger.error(f"Error al cargar el estado: {e}")
    
    def check_for_updates(self):
        """Verifica si hay actualizaciones en las playlists"""
        logger.info("Verificando actualizaciones de playlists...")
        
        # Resetear flag de cambios
        self.changes_detected = False
        
        try:
            # Preparar parámetros para la verificación
            params = {}
            if self.last_update:
                params["last_update"] = self.last_update
            
            if self.active_playlists:
                playlist_ids = ",".join([str(pid) for pid in self.active_playlists.keys()])
                params["playlist_ids"] = playlist_ids
            
            # Obtener actualizaciones del servidor
            logger.info(f"Solicitando playlists activas de: {self.server_url}/api/raspberry/playlists/active")
            response = requests.get(
                f"{self.server_url}/api/raspberry/playlists/active", 
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Error al obtener actualizaciones: {response.status_code}")
                return
            
            # Procesar playlists activas
            active_playlists = response.json()
            logger.info(f"Recibidas {len(active_playlists)} playlists activas")
            
            # Identificar playlists nuevas o modificadas
            playlists_to_update = []
            for playlist in active_playlists:
                playlist_id = str(playlist["id"])
                
                # Verificar si es una playlist nueva o modificada
                if playlist_id not in self.active_playlists:
                    logger.info(f"Nueva playlist encontrada: {playlist['title']} (ID: {playlist_id})")
                    playlists_to_update.append(playlist)
                    self.changes_detected = True
                else:
                    # Comparar para ver si ha sido modificada
                    old_playlist = self.active_playlists[playlist_id]
                    
                    # Verificar si hay cambios en los videos de la playlist
                    old_videos = {str(v["id"]): v for v in old_playlist.get("videos", [])}
                    new_videos = {str(v["id"]): v for v in playlist.get("videos", [])}
                    
                    if len(old_videos) != len(new_videos):
                        logger.info(f"Cambio en el número de videos en playlist: {playlist['title']} (ID: {playlist_id})")
                        playlists_to_update.append(playlist)
                        self.changes_detected = True
                    else:
                        # Verificar si hay nuevos videos o videos modificados
                        for video_id, video in new_videos.items():
                            if video_id not in old_videos:
                                logger.info(f"Nuevo video en playlist {playlist_id}: Video ID {video_id}")
                                playlists_to_update.append(playlist)
                                self.changes_detected = True
                                break
                            # También podríamos verificar si los videos han cambiado
                            # (por ejemplo, verificando fechas o metadatos)
            
            # Identificar playlists expiradas
            expired_playlists = []
            for playlist_id in list(self.active_playlists.keys()):
                if not any(str(p["id"]) == playlist_id for p in active_playlists):
                    logger.info(f"Playlist expirada o eliminada: ID {playlist_id}")
                    expired_playlists.append(playlist_id)
                    self.changes_detected = True
            
            # Procesar playlists expiradas
            for playlist_id in expired_playlists:
                self.remove_playlist(playlist_id)
            
            # Descargar playlists nuevas o modificadas
            for playlist in playlists_to_update:
                self.download_playlist(playlist)
            
            # Actualizar lista de playlists activas
            self.active_playlists = {str(p["id"]): p for p in active_playlists}
            self.last_update = datetime.now().isoformat()
            
            # Actualizar estado en el sistema de archivos
            self.save_state()
            
            logger.info(f"Sincronización completada. Total playlists activas: {len(self.active_playlists)}")
            logger.info(f"¿Se detectaron cambios? {'Sí' if self.changes_detected else 'No'}")
            
        except Exception as e:
            logger.error(f"Error durante la verificación de actualizaciones: {e}")
            logger.error(traceback.format_exc())
    
    def save_state(self):
        """Guarda el estado actual del cliente"""
        state_file = os.path.join(self.download_path, "client_state.json")
        
        try:
            state = {
                "active_playlists": self.active_playlists,
                "last_update": self.last_update,
                "last_sync": datetime.now().isoformat()
            }
            
            with open(state_file, "w") as f:
                json.dump(state, f, indent=4)
            
            logger.debug("Estado guardado correctamente")
        except Exception as e:
            logger.error(f"Error al guardar el estado: {e}")
    
    def download_playlist(self, playlist):
        """Descarga una playlist y sus videos"""
        playlist_id = str(playlist["id"])
        logger.info(f"Descargando playlist {playlist_id}: {playlist['title']}")
        
        # Crear directorio para la playlist
        playlist_dir = os.path.join(self.playlists_path, playlist_id)
        os.makedirs(playlist_dir, exist_ok=True)
        
        # Guardar información de la playlist
        playlist_file = os.path.join(playlist_dir, "playlist.json")
        with open(playlist_file, "w") as f:
            json.dump(playlist, f, indent=4)
        
        # Descargar videos
        for video in playlist.get("videos", []):
            video_id = str(video["id"])
            video_filename = f"{video_id}.mp4"
            video_path = os.path.join(playlist_dir, video_filename)
            
            # Si el video ya existe y tiene tamaño mayor que cero, omitir descarga
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                logger.debug(f"Video {video_id} ya existe, omitiendo descarga")
                continue
            
            # Descargar el video
            try:
                video_url = f"{self.server_url}/api/videos/{video_id}/download"
                logger.info(f"Descargando video {video_id}: {video['title']}")
                
                with requests.get(video_url, stream=True, timeout=120) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    
                    # Crear archivo temporal para la descarga
                    temp_path = f"{video_path}.tmp"
                    
                    # Descargar en chunks para archivos grandes
                    downloaded = 0
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Mostrar progreso cada 5%
                                if total_size > 0 and downloaded % (total_size // 20) < 8192:
                                    progress = (downloaded / total_size) * 100
                                    logger.info(f"Progreso de descarga {video_id}: {progress:.1f}%")
                    
                    # Mover archivo temporal a destino final
                    os.rename(temp_path, video_path)
                    logger.info(f"Video {video_id} descargado correctamente")
                    
                    # Marcar que se detectaron cambios
                    self.changes_detected = True
            
            except Exception as e:
                logger.error(f"Error al descargar video {video_id}: {e}")
                # Eliminar archivo temporal si existe
                if os.path.exists(f"{video_path}.tmp"):
                    os.remove(f"{video_path}.tmp")
        
        # Crear archivo m3u con rutas absolutas
        self.create_m3u_playlist(playlist, playlist_dir)
        
        logger.info(f"Playlist {playlist_id} descargada correctamente")
    
    def create_m3u_playlist(self, playlist, playlist_dir):
        """Crea un archivo m3u con la lista de videos"""
        m3u_path = os.path.join(playlist_dir, "playlist.m3u")
        
        # Guardar contenido anterior para verificar cambios
        old_content = ""
        if os.path.exists(m3u_path):
            with open(m3u_path, "r") as f:
                old_content = f.read()
        
        # Recopilar rutas de videos
        video_paths = []
        for video in playlist.get("videos", []):
            video_id = str(video["id"])
            video_path = os.path.join(playlist_dir, f"{video_id}.mp4")
            
            if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                # Usar ruta absoluta para mayor compatibilidad
                video_absolute_path = os.path.abspath(video_path)
                video_paths.append(video_absolute_path)
        
        # Crear archivo m3u
        if video_paths:
            new_content = "\n".join(video_paths)
            
            # Verificar si el contenido ha cambiado
            if new_content != old_content:
                with open(m3u_path, "w") as f:
                    f.write(new_content)
                
                logger.info(f"Archivo m3u actualizado con {len(video_paths)} videos")
                self.changes_detected = True
            else:
                logger.debug("Archivo m3u sin cambios")
        else:
            logger.warning(f"No se encontraron videos válidos para crear el archivo m3u")
        
        # Copiar el script de reproducción mejorado
        self.create_play_script(playlist_dir)
    
    def create_play_script(self, playlist_dir):
        """Crea o actualiza el script play_videos.sh en el directorio de la playlist"""
        script_path = os.path.join(playlist_dir, "play_videos.sh")
        
        # Contenido del script
        script_content = """#!/bin/bash
# Script avanzado para reproducir videos en bucle
# Verifica múltiples reproductores y usa el primero disponible

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "===== Reproductor de Videos ====="
echo "Directorio: $(pwd)"
echo "Fecha: $(date)"

# Verificar si existe la playlist m3u
if [ ! -f "playlist.m3u" ]; then
  echo "Error: playlist.m3u no encontrada"
  exit 1
fi

# Contar videos en la playlist
NUM_VIDEOS=$(grep -c . playlist.m3u)
echo "Encontrados $NUM_VIDEOS videos en la playlist"

# Mostrar contenido de la playlist
echo "Contenido de playlist.m3u:"
cat playlist.m3u

# Función para verificar si un comando está disponible
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Intentar reproducir con VLC (primera opción)
if command_exists cvlc || command_exists vlc; then
  echo "Usando VLC para reproducción..."
  
  if command_exists cvlc; then
    echo "Ejecutando: cvlc --loop --no-video-title-show --fullscreen playlist.m3u"
    exec cvlc --loop --no-video-title-show --fullscreen playlist.m3u
  else
    echo "Ejecutando: vlc --loop --no-video-title-show --fullscreen --started-from-file playlist.m3u"
    exec vlc --loop --no-video-title-show --fullscreen --started-from-file playlist.m3u
  fi

# Intentar con MPV
elif command_exists mpv; then
  echo "Usando MPV para reproducción..."
  echo "Ejecutando: mpv --fullscreen --loop-playlist=inf playlist.m3u"
  exec mpv --fullscreen --loop-playlist=inf playlist.m3u

# Intentar con SMPlayer
elif command_exists smplayer; then
  echo "Usando SMPlayer para reproducción..."
  echo "Ejecutando: smplayer -fullscreen -loop playlist.m3u"
  exec smplayer -fullscreen -loop playlist.m3u

# Intentar con OMXPlayer (Raspberry Pi)
elif command_exists omxplayer; then
  echo "Usando OMXPlayer para reproducción (Raspberry Pi)..."
  echo "OMXPlayer no soporta archivos m3u directamente, reproduciendo videos individualmente..."
  
  while true; do
    while read -r video_path; do
      # Ignorar líneas vacías
      if [ -z "$video_path" ]; then
        continue
      fi
      
      echo "Reproduciendo: $video_path"
      if [ -f "$video_path" ]; then
        omxplayer -o hdmi --no-osd --no-keys "$video_path"
      else
        echo "Advertencia: El archivo $video_path no existe"
      fi
      
      # Pequeña pausa entre videos
      sleep 1
    done < playlist.m3u
    
    echo "Playlist completada, reiniciando..."
    sleep 2
  done

# Intentar con MPlayer
elif command_exists mplayer; then
  echo "Usando MPlayer para reproducción..."
  echo "Ejecutando: mplayer -fs -loop 0 -playlist playlist.m3u"
  exec mplayer -fs -loop 0 -playlist playlist.m3u

else
  echo "Error: No se encontró ningún reproductor de video compatible"
  echo "Por favor, instale VLC, MPV, SMPlayer, OMXPlayer o MPlayer"
  exit 1
fi
"""
        
        # Escribir el script
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Hacer el script ejecutable
        os.chmod(script_path, 0o755)
        
        logger.debug(f"Script de reproducción creado/actualizado: {script_path}")
    
    def remove_playlist(self, playlist_id):
        """Elimina una playlist expirada"""
        logger.info(f"Eliminando playlist {playlist_id}")
        
        # Marcar la playlist como inactiva pero mantener los archivos
        if playlist_id in self.active_playlists:
            del self.active_playlists[playlist_id]
        
        # Opcionalmente, si se quieren eliminar los archivos, descomentar lo siguiente:
        """
        playlist_dir = os.path.join(self.playlists_path, playlist_id)
        if os.path.exists(playlist_dir):
            try:
                for file in os.listdir(playlist_dir):
                    file_path = os.path.join(playlist_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(playlist_dir)
                logger.info(f"Directorio de playlist {playlist_id} eliminado")
            except Exception as e:
                logger.error(f"Error al eliminar directorio de playlist {playlist_id}: {e}")
        """
    
    def restart_videoloop_service(self):
        """Reinicia el servicio de reproducción de video"""
        logger.info(f"Reiniciando servicio {self.service_name}...")
        
        try:
            # Verificar si el servicio existe
            check_cmd = ["systemctl", "status", self.service_name]
            check_result = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if check_result.returncode == 4:  # 4 indica que el servicio no existe
                logger.warning(f"El servicio {self.service_name} no existe")
                return
            
            # Reiniciar el servicio
            restart_cmd = ["sudo", "systemctl", "restart", self.service_name]
            restart_result = subprocess.run(restart_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if restart_result.returncode == 0:
                logger.info(f"Servicio {self.service_name} reiniciado correctamente")
            else:
                error = restart_result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"Error al reiniciar el servicio: {error}")
                
                # Intento alternativo con sudo explícito por si hay problemas de permisos
                if "permission denied" in error.lower():
                    logger.info("Intentando reiniciar con sudo explícito...")
                    os.system(f"echo 'Reiniciando servicio desde script' | sudo -S systemctl restart {self.service_name}")
                    logger.info("Comando de reinicio alternativo ejecutado")
        
        except Exception as e:
            logger.error(f"Error al intentar reiniciar el servicio: {e}")

def main():
    parser = argparse.ArgumentParser(description="Cliente de sincronización de videos")
    parser.add_argument("--server", required=True, help="URL del servidor")
    parser.add_argument("--download-path", default="./downloads", help="Ruta de descarga")
    parser.add_argument("--check-interval", type=int, default=30, 
                        help="Intervalo de verificación en minutos")
    parser.add_argument("--service", default="videoloop.service",
                        help="Nombre del servicio a reiniciar cuando hay cambios")
    
    args = parser.parse_args()
    
    client = VideoDownloaderClient(
        server_url=args.server,
        download_path=args.download_path,
        check_interval=args.check_interval,
        service_name=args.service
    )
    
    client.start()

if __name__ == "__main__":
    main()