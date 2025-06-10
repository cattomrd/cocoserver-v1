import asyncio
import logging
from sqlalchemy.orm import Session
import paramiko
import os
from dotenv import load_dotenv

from models import models
from models.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Enviar logs a la consola
    ]
)

logger = logging.getLogger(__name__)
load_dotenv()
# Configuración SSH mejorada
# Usar variables de entorno con valores predeterminados como respaldo
SSH_USER = os.environ.get('SSH_USER')
SSH_PASSWORD = os.environ.get('SSH_PASSWORD')
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '/path/to/ssh/key')  # Ruta a la clave SSH privada
SSH_PORT = int(os.environ.get('SSH_PORT', 22))


# Verificar si las variables críticas están definidas
if not SSH_USER:
    logger.warning("SSH_USER no está definido en las variables de entorno. Se requerirá en cada operación SSH.")
    
if not SSH_PASSWORD:
    logger.warning("SSH_PASSWORD no está definido en las variables de entorno. Se requerirá en cada operación SSH si no se usa clave SSH.")

async def validate_ssh_credentials(device_id):
    """
    Verifica que se tienen las credenciales SSH necesarias para un dispositivo
    Intenta primero con WiFi, si falla intenta con LAN
    
    Args:
        device_id (str): ID del dispositivo
        
    Returns:
        dict: Resultado de la validación

    """
    logger.info(f"Intentando validar credenciales SSH para dispositivo {device_id}")
    logger.info(f"Usando SSH_USER: {SSH_USER}")
    logger.info(f"SSH_PASSWORD está definido: {'Sí' if SSH_PASSWORD else 'No'}")
    logger.info(f"SSH_KEY_PATH: {SSH_KEY_PATH}")
    logger.info(f"SSH_PORT: {SSH_PORT}")
    db = SessionLocal()
    try:
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if not device:
            return {'success': False, 'message': 'Dispositivo no encontrado'}
        
        if not device.is_active:
            return {'success': False, 'message': 'El dispositivo no está activo'}
        
        # Probar conexión SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Lista de IPs para intentar, primero WiFi, luego LAN
        ip_addresses = []
        if device.ip_address_wifi:
            ip_addresses.append(('WiFi', device.ip_address_wifi))
        if device.ip_address_lan:
            ip_addresses.append(('LAN', device.ip_address_lan))
        
        if not ip_addresses:
            return {'success': False, 'message': 'No hay direcciones IP disponibles para conectar'}
        
        # Intentar cada IP hasta que una funcione
        connection_errors = []
        for connection_type, ip_address in ip_addresses:
            try:
                logger.info(f"Intentando conectar vía SSH a {connection_type} ({ip_address})")
                
                # Intentar conectar con clave SSH primero
                if os.path.exists(SSH_KEY_PATH):
                    key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
                    ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, pkey=key, timeout=5)
                else:
                    # Si no hay clave, usar contraseña
                    ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=5)
                
                # Si llegamos aquí, la conexión fue exitosa
                logger.info(f"Conexión SSH exitosa a {connection_type} ({ip_address})")
                
                # Probar si podemos usar sudo
                stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S echo "OK"')
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                
                # Cerrar conexión SSH
                ssh.close()
                
                if 'OK' in output:
                    return {
                        'success': True, 
                        'message': f'Credenciales SSH válidas con permisos sudo (vía {connection_type})',
                        'connection_type': connection_type,
                        'ip_address': ip_address
                    }
                else:
                    return {
                        'success': False, 
                        'message': f'Conexión SSH exitosa a {connection_type} ({ip_address}), pero sin permisos sudo: {error}',
                    }
                    
            except Exception as e:
                # Registrar el error y continuar con la siguiente IP
                error_msg = f"Error al conectar por SSH a {connection_type} ({ip_address}): {str(e)}"
                logger.warning(error_msg)
                connection_errors.append(error_msg)
                continue
        
        # Si llegamos aquí, ninguna conexión funcionó
        error_details = "\n".join(connection_errors)
        logger.error(f"No se pudo establecer conexión SSH con ninguna interfaz: {error_details}")
        return {'success': False, 'message': f'Error de conexión SSH a todas las interfaces disponibles'}
        
    finally:
        db.close()
    
async def restart_host(device_id):
    """
    Reinicia el dispositivo
    """
    logger.info(f"Reiniciando dispositivo {device_id}")
    db = SessionLocal()
    try:
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if not device:
            return {'success': False, 'message': 'Dispositivo no encontrado'}
        
        if not device.is_active:
            return {'success': False, 'message': 'El dispositivo no está activo'}
        
        # Determinar el tipo de dispositivo
        device_type = "unknown"

        ssh_validation = await validate_ssh_credentials(device_id)
        if not ssh_validation['success']:
            return {'success': False, 'message': f'Error de validación SSH: {ssh_validation["message"]}'}
        
        # Usar la interfaz que funcionó en la validación
        connection_type = ssh_validation.get('connection_type', 'LAN')
        ip_address = ssh_validation.get('ip_address', device.ip_address_lan or device.ip_address_wifi)
        
        logger.info(f"Reiniciando el cliente vía {connection_type} ({ip_address})")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if os.path.exists(SSH_KEY_PATH):
                key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, pkey=key, timeout=10)
            else:
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=10)

            # Reinicia el dispositivo
            stdin, stdout, stderr = ssh.exec_command('sudo reboot')
            os_info = stdout.read().decode()

            return {'success': True, 'message': f'Reinicio del dispositivo {device_id} iniciado'}

        except Exception as e:
            logger.error(f"Error al reiniciar el dispositivo {device_id}: {str(e)}")
            return {'success': False, 'message': f'Error al reiniciar el dispositivo: {str(e)}'}

    finally:
        db.close()  
        ssh.close()