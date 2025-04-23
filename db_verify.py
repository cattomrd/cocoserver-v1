# db_verify.py - Script para verificar la integridad de la base de datos

import os
import sys
import logging
from sqlalchemy import inspect, MetaData, create_engine
from sqlalchemy.orm import sessionmaker

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DB-Verify")

# URL de la base de datos (ajusta según tu configuración)
DATABASE_URL = "sqlite:///./RaspDatos.db"  # Por defecto

def verify_database(db_url=None):
    """Verifica la estructura e integridad de la base de datos"""
    
    if db_url is None:
        db_url = DATABASE_URL
    
    logger.info(f"Conectando a la base de datos: {db_url}")
    
    try:
        # Conectar a la base de datos
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Obtener un inspector
        inspector = inspect(engine)
        
        # Verificar las tablas existentes
        tables = inspector.get_table_names()
        logger.info(f"Tablas encontradas: {tables}")
        
        # Verificar tablas requeridas
        required_tables = ['videos', 'playlists', 'playlist_videos', 'device_playlists', 'devices']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"Faltan tablas requeridas: {missing_tables}")
            return False
        
        # Verificar estructura de la tabla videos
        columns = {col['name']: col for col in inspector.get_columns('videos')}
        logger.info(f"Columnas de la tabla videos: {list(columns.keys())}")
        
        # Verificar columnas requeridas
        required_columns = ['id', 'title', 'file_path', 'file_size', 'upload_date']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error(f"Faltan columnas requeridas en la tabla videos: {missing_columns}")
            return False
        
        # Verificar índices primarios
        pk = inspector.get_pk_constraint('videos')
        if not pk or 'id' not in pk['constrained_columns']:
            logger.error("La tabla videos no tiene una clave primaria correcta")
            return False
        
        # Verificar contenido básico
        from models.models import Video
        video_count = session.query(Video).count()
        logger.info(f"Número de videos en la base de datos: {video_count}")
        
        if video_count > 0:
            # Verificar un video de ejemplo
            sample_video = session.query(Video).first()
            logger.info(f"Video de ejemplo: ID={sample_video.id}, Título={sample_video.title}")
            logger.info(f"Ruta de archivo: {sample_video.file_path}")
            
            # Verificar si el archivo existe
            if not os.path.exists(sample_video.file_path):
                logger.warning(f"El archivo {sample_video.file_path} no existe")
        
        # Comprobar relaciones
        from models.models import Playlist, PlaylistVideo, DevicePlaylist, Device
        
        # Verificar integridad de las relaciones
        playlist_count = session.query(Playlist).count()
        playlist_video_count = session.query(PlaylistVideo).count()
        device_count = session.query(Device).count()
        device_playlist_count = session.query(DevicePlaylist).count()
        
        logger.info(f"Playlists: {playlist_count}")
        logger.info(f"Relaciones Playlist-Video: {playlist_video_count}")
        logger.info(f"Dispositivos: {device_count}")
        logger.info(f"Relaciones Device-Playlist: {device_playlist_count}")
        
        # Todo parece estar bien
        logger.info("Verificación de base de datos completada sin errores")
        return True
        
    except Exception as e:
        logger.error(f"Error al verificar la base de datos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # Cerrar la sesión
        if 'session' in locals():
            session.close()

def recreate_database():
    """Recrear la base de datos (¡CUIDADO! Eliminará todos los datos)"""
    logger.warning("RECREANDO LA BASE DE DATOS - TODOS LOS DATOS SERÁN ELIMINADOS")
    
    try:
        # Conectar a la base de datos
        engine = create_engine(DATABASE_URL)
        
        # Importar los modelos
        from models.models import Base
        
        # Eliminar todas las tablas
        Base.metadata.drop_all(engine)
        logger.info("Tablas eliminadas")
        
        # Crear todas las tablas
        Base.metadata.create_all(engine)
        logger.info("Tablas recreadas")
        
        return True
    except Exception as e:
        logger.error(f"Error al recrear la base de datos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verificador de base de datos")
    parser.add_argument("--db-url", help="URL de la base de datos SQLAlchemy")
    parser.add_argument("--recreate", action="store_true", help="Recrear la base de datos (¡ELIMINA TODOS LOS DATOS!)")
    
    args = parser.parse_args()
    
    if args.recreate:
        confirm = input("¿Estás seguro de que quieres recrear la base de datos? "
                    "Todos los datos se perderán. Escribe 'RECREAR' para confirmar: ")
        if confirm == "RECREAR":
            if recreate_database():
                logger.info("Base de datos recreada correctamente")
            else:
                logger.error("Error al recrear la base de datos")
        else:
            logger.info("Operación cancelada")
    else:
        verify_database(args.db_url)

if __name__ == "__main__":
    main()