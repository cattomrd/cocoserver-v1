# Cliente actualizado para Raspberry Pi (client/client.py)

import os
import sys
import json
import time
import requests
import schedule
from datetime import datetime
import subprocess
import argparse
import logging
import traceback

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("raspberry_client.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RaspberryClient")

class VideoPlayerClient:
    def __init__(self, server_url, download_path, check_interval=30):
        """
        Inicializa el cliente para Raspberry Pi
        
        Args:
            server_url (str): URL del servidor de videos
            download_path (str): Ruta donde se guardarán los videos descargados
            check_interval (int): Intervalo en minutos para verificar actualizaciones
        """
        self.server_url = server_url
        self.download_path = download_path
        self.check_interval = check_interval
        self.playlists_path = os.path.join(download_path, "playlists")
        self.videos_path = os.path.join(download_path, "videos")
        
        # Crear directorios si no existen
        os.makedirs(self.playlists_path, exist_ok=True)
        os.makedirs(self.videos_path, exist_ok=True)
        
        # Lista local de playlists activas
        self.active_playlists = {}
        
        # Estado del cliente
        self.last_update = None
        
        # Cargar datos guardados previamente
        self.load_saved_state()
        
        # Video en reproducción actual
        self.currently_playing = None
        self.current_playlist = None
    
    def load_saved_state(self):
        """Carga el estado guardado del cliente"""
        state_file = os.path.join(self.download_path, "client_state.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
                    self.active_playlists = state.get("active_playlists", {})
                    self.last_update = state.get("last_update")
                logger.info(f"Estado cargado: {len(self.active_playlists)} playlists encontradas")
            except Exception as e:
                logger.error(f"Error al cargar el estado: {e}")
                self.active_playlists = {}
                self.last_update = None
    
    def save_state(self):
        """Guarda el estado actual del cliente"""
        state_file = os.path.join(self.download_path, "client_state.json")
        
        try:
            state = {
                "active_playlists": self.active_playlists,
                "last_update": datetime.now().isoformat()
            }
            
            with open(state_file, "w") as f:
                json.dump(state, f, indent=4)
            
            logger.info("Estado guardado correctamente")
        except Exception as e:
            logger.error(f"Error al guardar el estado: {e}")
    
    # En la función check_for_updates del cliente
    def check_for_updates(self):
        """Verifica si hay actualizaciones en las playlists"""
        logger.info("Verificando actualizaciones de playlists...")
        
        try:
            # Preparar parámetros para la verificación
            params = {}
            if self.last_update:
                params["last_update"] = self.last_update
            
            if self.active_playlists:
                playlist_ids = ",".join([str(pid) for pid in self.active_playlists.keys()])
                params["playlist_ids"] = playlist_ids
            
            # Obtener actualizaciones del servidor
            logger.info(f"Solicitando actualizaciones a: {self.server_url}/api/raspberry/check-updates")
            response = requests.get(
                f"{self.server_url}/api/raspberry/check-updates", 
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"Error al obtener actualizaciones: {response.status_code}")
                return
            
            data = response.json()
            
            # Comprobar el tipo de respuesta
            if isinstance(data, list):
                # Si es una lista, asumimos que son playlists activas
                logger.info(f"Formato lista detectado. Playlists activas: {len(data)}")
                
                # Actualizar el diccionario de playlists activas
                new_active_playlists = {}
                for playlist in data:
                    playlist_id = str(playlist["id"])
                    new_active_playlists[playlist_id] = playlist
                    self.download_playlist(playlist)
                
                # Actualizar la lista completa de playlists activas
                self.active_playlists = new_active_playlists
                
            else:
                # Si es un diccionario, extraemos los valores
                active_playlists = data.get("active_playlists", [])
                expired_playlist_ids = data.get("expired_playlists", [])
                logger.info(f"Formato diccionario detectado. Playlists activas: {len(active_playlists)}, expiradas: {len(expired_playlist_ids)}")
                self.last_update = data.get("timestamp", datetime.now().isoformat())
                
                # Procesar playlists expiradas
                if expired_playlist_ids:
                    logger.info(f"Encontradas {len(expired_playlist_ids)} playlists expiradas")
                    for playlist_id in expired_playlist_ids:
                        self.remove_playlist(str(playlist_id))
                
                # Procesar playlists activas/actualizadas
                if active_playlists:
                    logger.info(f"Encontradas {len(active_playlists)} playlists activas/actualizadas")
                    for playlist in active_playlists:
                        playlist_id = str(playlist["id"])
                        logger.info(f"Procesando playlist ID {playlist_id}: {playlist['title']}")
                        
                        # Actualizar o agregar la playlist
                        self.active_playlists[playlist_id] = playlist
                        self.download_playlist(playlist)
            
            # Guardar estado actual
            self.save_state()
            logger.info(f"Actualización completada. Total playlists activas: {len(self.active_playlists)}")
            
        except Exception as e:    
            logger.error(f"Error durante la verificación de actualizaciones: {e}")
            logger.error(traceback.format_exc())
    
    def update_playlist(self, playlist):
        """
        Actualiza una playlist existente
        
        Args:
            playlist (dict): Datos actualizados de la playlist
        """
        playlist_id = str(playlist["id"])
        logger.info(f"Actualizando playlist {playlist_id}: {playlist['title']}")
        
        # Directorio de la playlist
        playlist_dir = os.path.join(self.playlists_path, playlist_id)
        os.makedirs(playlist_dir, exist_ok=True)
        
        # Cargar datos actuales
        playlist_file = os.path.join(playlist_dir, "playlist.json")
        current_videos = {}
        
        if os.path.exists(playlist_file):
            try:
                with open(playlist_file, "r") as f:
                    current_data = json.load(f)
                    current_videos = {str(v["id"]): v for v in current_data.get("videos", [])}
            except Exception as e:
                logger.error(f"Error al leer playlist actual: {e}")
                current_videos = {}
        
        # Actualizar el archivo de la playlist
        with open(playlist_file, "w") as f:
            json.dump(playlist, f, indent=4)
        
        # Guardar en la lista de playlists activas
        self.active_playlists[playlist_id] = playlist
        
        # Identificar videos nuevos
        new_videos = []
        for video in playlist.get("videos", []):
            if str(video["id"]) not in current_videos:
                new_videos.append(video)
        
        # Descargar solo los videos nuevos
        for video in new_videos:
            self.download_video(video, playlist_dir)
        
        logger.info(f"Playlist {playlist_id} actualizada con {len(new_videos)} nuevos videos")
    

    def download_video(self, video, playlist_dir):
        """
        Descarga un video desde el servidor y lo guarda localmente
        
        Args:
            video (dict): Diccionario con los datos del video
            playlist_dir (str): Directorio donde se guardará el video
        """
        video_id = str(video["id"])
        video_filename = f"{video_id}.mp4"
        video_path = os.path.join(playlist_dir, video_filename)
        
        # Verificar si el video ya existe
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            # Verificar si el archivo está completo (opcional)
            if file_size > 0:  # Podrías comparar con video.get("size") si está disponible
                logger.info(f"Video {video_id} ya existe, omitiendo descarga")
                return
        
        # URL completa del video
        video_url = f"{self.server_url}/api/videos/{video_id}/download"
        temp_path = f"{video_path}.tmp"
        
        try:
            logger.info(f"Iniciando descarga de video {video_id}: {video['title']}")
            logger.info(f"URL de descarga: {video_url}")
            
            # Configurar headers para manejar descargas parciales
            headers = {}
            if os.path.exists(temp_path):
                downloaded_size = os.path.getsize(temp_path)
                headers['Range'] = f'bytes={downloaded_size}-'
            
            # Realizar la solicitud con stream=True para descargar en chunks
            with requests.get(video_url, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status()  # Lanza excepción para códigos 4XX/5XX
                
                # Verificar si es una descarga parcial (206) o completa (200)
                if response.status_code == 206:
                    mode = 'ab'  # Append si es descarga parcial
                    total_size = int(response.headers.get('content-range').split('/')[1])
                else:
                    mode = 'wb'  # Write nuevo archivo
                    total_size = int(response.headers.get('content-length', 0))
                
                # Mostrar información de la descarga
                logger.info(f"Tamaño total: {total_size} bytes")
                logger.info(f"Modo de descarga: {'resume' if mode == 'ab' else 'new'}")
                
                # Descargar en chunks y mostrar progreso
                downloaded = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
                chunk_size = 8192  # 8KB chunks
                
                with open(temp_path, mode) as file:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:  # Filtrar keep-alive chunks
                            file.write(chunk)
                            downloaded += len(chunk)
                            # Log progreso cada 1MB
                            if downloaded % (1024*1024) < chunk_size:
                                logger.info(f"Descargados {downloaded}/{total_size} bytes ({downloaded/total_size:.1%})")
                
                # Renombrar el archivo temporal al finalizar
                os.rename(temp_path, video_path)
                logger.info(f"Video {video_id} descargado correctamente en {video_path}")
                
                # Verificar integridad del archivo (opcional)
                actual_size = os.path.getsize(video_path)
                if total_size > 0 and actual_size != total_size:
                    logger.warning(f"Tamaño del archivo ({actual_size}) no coincide con el esperado ({total_size})")
                    os.remove(video_path)
                    raise IOError("Tamaño del archivo incorrecto")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al descargar video {video_id}: {str(e)}")
            # Intentar eliminar el archivo temporal si hubo error
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise
        
        except Exception as e:
            logger.error(f"Error inesperado al descargar video {video_id}: {str(e)}")
            logger.error(traceback.format_exc())
            raise
 
    def download_playlist(self, playlist):
        """
        Descarga o actualiza una playlist y sus videos
        
        Args:
            playlist (dict): Diccionario con los datos de la playlist
        """
        playlist_id = str(playlist["id"])
        logger.info(f"Descargando/actualizando playlist {playlist_id}: {playlist['title']}")
        
        # Crear directorio para la playlist
        playlist_dir = os.path.join(self.playlists_path, playlist_id)
        os.makedirs(playlist_dir, exist_ok=True)
        
        # Guardar información de la playlist
        playlist_file = os.path.join(playlist_dir, "playlist.json")
        
        # Verificar si la playlist ya existe
        existing_videos = {}
        if os.path.exists(playlist_file):
            try:
                with open(playlist_file, "r") as f:
                    existing_data = json.load(f)
                    # Crear un diccionario de videos existentes para comparar
                    existing_videos = {str(v["id"]): v for v in existing_data.get("videos", [])}
                logger.info(f"Playlist existente encontrada con {len(existing_videos)} videos")
            except Exception as e:
                logger.error(f"Error al leer playlist existente: {e}")
        
        # Guardar la información actualizada de la playlist
        with open(playlist_file, "w") as f:
            json.dump(playlist, f, indent=4)
        
        logger.info(f"Información de playlist guardada en {playlist_file}")
        
        # Agregar a las playlists activas
        self.active_playlists[playlist_id] = playlist
        
        # Descargar videos que no existen localmente
        videos_to_download = []
        for video in playlist.get("videos", []):
            video_id = str(video["id"])
            # Verificar si el video ya existe
            if video_id in existing_videos:
                # Si el video ya existe, verificar si hay cambios (por ejemplo, en el título o fecha de expiración)
                if (video.get("title") != existing_videos[video_id].get("title") or 
                    video.get("expiration_date") != existing_videos[video_id].get("expiration_date")):
                    logger.info(f"Video {video_id} requiere actualización de metadatos")
                    videos_to_download.append(video)
            else:
                # Si es un video nuevo, agregarlo a la lista de descarga
                videos_to_download.append(video)
        
        if not videos_to_download:
            logger.info(f"No hay nuevos videos para descargar en la playlist {playlist_id}")
            return
        
        # Descargar los videos nuevos o actualizados
        logger.info(f"Descargando {len(videos_to_download)} videos para la playlist {playlist_id}")
        for video in videos_to_download:
            try:
                self.download_video(video, playlist_dir)
            except Exception as e:
                logger.error(f"Error al descargar video {video.get('id')}: {e}")
        
        logger.info(f"Playlist {playlist_id} descargada/actualizada correctamente")

    def remove_playlist(self, playlist_id):
        """
        Elimina una playlist expirada
        
        Args:
            playlist_id (str): ID de la playlist a eliminar
        """
        logger.info(f"Eliminando playlist {playlist_id}")
        
        # Detener reproducción si es la playlist actual
        if self.current_playlist == playlist_id:
            self.stop_playback()
            self.current_playlist = None
        
        # Directorio de la playlist
        playlist_dir = os.path.join(self.playlists_path, playlist_id)
        
        # Eliminar el directorio si existe
        if os.path.exists(playlist_dir):
            try:
                for file in os.listdir(playlist_dir):
                    os.remove(os.path.join(playlist_dir, file))
                os.rmdir(playlist_dir)
                logger.info(f"Playlist {playlist_id} eliminada correctamente")
            except Exception as e:
                logger.error(f"Error al eliminar playlist {playlist_id}: {e}")
        
        # Eliminar de la lista de playlists activas
        if playlist_id in self.active_playlists:
            del self.active_playlists[playlist_id]
    
    def play_playlist(self, playlist_id):
        """
        Reproduce los videos de una playlist
        
        Args:
            playlist_id (str): ID de la playlist
        """
        playlist_dir = os.path.join(self.playlists_path, playlist_id)
        playlist_file = os.path.join(playlist_dir, "playlist.json")
        
        if not os.path.exists(playlist_file):
            logger.error(f"Playlist {playlist_id} no encontrada")
            return
        
        try:
            with open(playlist_file, "r") as f:
                playlist = json.load(f)
            
            # Verificar si la playlist ha expirado
            if playlist.get("expiration_date"):
                expiration_date = datetime.fromisoformat(playlist["expiration_date"].replace('Z', '+00:00'))
                if datetime.now() > expiration_date:
                    logger.warning(f"La playlist {playlist_id} ha expirado: {playlist['title']}")
                    self.remove_playlist(playlist_id)
                    return
            
            # Establecer como playlist actual
            self.current_playlist = playlist_id
            
            logger.info(f"Reproduciendo playlist: {playlist['title']}")
            
            # Filtrar videos que no han expirado
            active_videos = []
            for video in playlist.get("videos", []):
                if video.get("expiration_date"):
                    expiration_date = datetime.fromisoformat(video["expiration_date"].replace('Z', '+00:00'))
                    if datetime.now() > expiration_date:
                        logger.warning(f"Video {video['id']} ha expirado: {video['title']}")
                        continue
                
                video_path = os.path.join(playlist_dir, f"{video['id']}.mp4")
                if os.path.exists(video_path):
                    active_videos.append((video, video_path))
            
            if not active_videos:
                logger.warning("No hay videos activos en esta playlist")
                return
            
            # Reproducir todos los videos de la playlist en bucle
            while self.current_playlist == playlist_id:
                for video, video_path in active_videos:
                    if self.current_playlist != playlist_id:
                        break  # Salir si se cambió la playlist
                    
                    logger.info(f"Reproduciendo video: {video['title']}")
                    self.currently_playing = video['id']
                    
                    # Reproducir el video
                    self.play_video(video_path)
                    
                    # Verificar actualizaciones después de cada video
                    self.check_for_updates()
                    
                    # Si la playlist ha sido eliminada o cambiada, salir
                    if self.current_playlist != playlist_id:
                        break
            
        except Exception as e:
            logger.error(f"Error al reproducir playlist: {e}")
    
    def play_video(self, video_path):
        """
        Reproduce un video utilizando el reproductor adecuado
        
        Args:
            video_path (str): Ruta al video a reproducir
        """
        try:
            # Usar omxplayer en Raspberry Pi o vlc en otros sistemas
            if os.path.exists("/usr/bin/omxplayer"):
                process = subprocess.Popen(["omxplayer", video_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                process.wait()
            else:
                process = subprocess.Popen(["cvlc", "-f", "--play-and-exit", "--video-on-top", "--no-video-title-show", video_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                process.wait()
            
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Error al reproducir video {video_path}: {e}")
            return False
    
    def stop_playback(self):
        """Detiene la reproducción actual"""
        if self.currently_playing:
            logger.info(f"Deteniendo reproducción del video {self.currently_playing}")
            
            # Matar procesos de reproducción
            try:
                if os.path.exists("/usr/bin/omxplayer"):
                    subprocess.run(["killall", "omxplayer.bin"], stderr=subprocess.PIPE)
                else:
                    subprocess.run(["killall", "vlc"], stderr=subprocess.PIPE)
            except Exception as e:
                logger.error(f"Error al detener reproducción: {e}")
            
            self.currently_playing = None
    
    def start_playback_loop(self):
        """Inicia el bucle de reproducción de playlists"""
        while True:
            if not self.active_playlists:
                logger.info("No hay playlists activas para reproducir")
                time.sleep(30)  # Esperar 30 segundos
                self.check_for_updates()
                continue
            
            # Reproducir todas las playlists en secuencia
            for playlist_id in list(self.active_playlists.keys()):
                # Si ya no está en las playlists activas, saltar
                if playlist_id not in self.active_playlists:
                    continue
                
                self.play_playlist(playlist_id)
    
    def start(self):
        """Inicia el cliente"""
        logger.info(f"Iniciando cliente para {self.server_url}")
        
        # Verificar inmediatamente al inicio
        self.check_for_updates()
        
        # Programar verificaciones periódicas
        schedule.every(self.check_interval).minutes.do(self.check_for_updates)
        
        # Iniciar thread para las verificaciones programadas
        import threading
        scheduler_thread = threading.Thread(target=self._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # Iniciar reproducción
        try:
            self.start_playback_loop()
        except KeyboardInterrupt:
            logger.info("Cliente detenido por el usuario")
        except Exception as e:
            logger.error(f"Error en el bucle principal: {e}")
        finally:
            self.stop_playback()
            self.save_state()
    
    def _run_scheduler(self):
        """Ejecuta el scheduler en un thread separado"""
        while True:
            schedule.run_pending()
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="Cliente de video para Raspberry Pi")
    parser.add_argument("--server", required=True, help="URL del servidor")
    parser.add_argument("--download-path", default="./downloads", help="Ruta donde se guardarán los videos")
    parser.add_argument("--check-interval", type=int, default=30, help="Intervalo en minutos para verificar actualizaciones")
    parser.add_argument("--play", help="Reproducir una playlist específica (ID)")
    
    args = parser.parse_args()
    
    client = VideoPlayerClient(
        server_url=args.server,
        download_path=args.download_path,
        check_interval=args.check_interval
    )
    
    if args.play:
        client.play_playlist(args.play)
    else:
        client.start()

if __name__ == "__main__":
    main()

