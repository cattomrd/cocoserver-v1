# /utils/hostname_changer.py
import asyncio
import logging
from sqlalchemy.orm import Session
import paramiko
import os
from dotenv import load_dotenv

from io import StringIO

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
SSH_PASSWORD = os.environ.get('SSH_PASS')
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '/path/to/ssh/key')  # Ruta a la clave SSH privada
SSH_PORT = int(os.environ.get('SSH_PORT', 22))  # Puerto SSH predeterminado

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

async def change_hostname(device_id, new_hostname):
    """
    Cambia el hostname de un dispositivo (Raspberry Pi o OrangePi)
    Adapta los comandos según el tipo de dispositivo
    
    Args:
        device_id (str): ID del dispositivo
        new_hostname (str): Nuevo hostname
        
    Returns:
        dict: Resultado de la operación
    """
    db = SessionLocal()
    try:
        # Buscar el dispositivo en la base de datos
        device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if not device:
            return {'success': False, 'message': 'Dispositivo no encontrado'}
        
        if not device.is_active:
            return {'success': False, 'message': 'El dispositivo no está activo'}
        
        # Determinar el tipo de dispositivo
        device_type = "unknown"
        if device.model and "raspberry" in device.model.lower():
            device_type = "raspberry"
        elif device.model and "orange" in device.model.lower():
            device_type = "orange"
            
        logger.info(f"Detectado dispositivo tipo: {device_type} (modelo: {device.model})")
        
        # Primero validar credenciales para determinar la mejor interfaz para conectar
        ssh_validation = await validate_ssh_credentials(device_id)
        if not ssh_validation['success']:
            return {'success': False, 'message': f'Error de validación SSH: {ssh_validation["message"]}'}
        
        # Usar la interfaz que funcionó en la validación
        connection_type = ssh_validation.get('connection_type', 'LAN')
        ip_address = ssh_validation.get('ip_address', device.ip_address_lan or device.ip_address_wifi)
        
        logger.info(f"Cambiando hostname vía {connection_type} ({ip_address})")
        
        # Conectar al dispositivo vía SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # Usar la misma conexión que funcionó en la validación
            if os.path.exists(SSH_KEY_PATH):
                key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, pkey=key, timeout=10)
            else:
                # Si no hay clave, usar contraseña
                ssh.connect(ip_address, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=10)
            
            # Verificar la distribución y comportamientos específicos
            stdin, stdout, stderr = ssh.exec_command('cat /etc/os-release')
            os_info = stdout.read().decode()
            
            # Comprobar si es Armbian (común en OrangePi)
            is_armbian = "Armbian" in os_info
            logger.info(f"Sistema operativo detectado: {'Armbian' if is_armbian else 'Raspbian/Otro'}")
            
            # 1. Cambiar en /etc/hostname
            logger.info("Cambiando hostname en /etc/hostname")
            stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S sh -c \'echo "{new_hostname}" > /etc/hostname\'')
            error = stderr.read().decode()
            if error and "denied" in error.lower():
                logger.error(f"Error al modificar /etc/hostname: {error}")
                return {'success': False, 'message': f'Error al modificar /etc/hostname: Permisos denegados'}
            
            # 2. Leer el contenido actual de /etc/hosts para modificarlo correctamente
            stdin, stdout, stderr = ssh.exec_command('cat /etc/hosts')
            hosts_content = stdout.read().decode()

            # Obtener el hostname actual para reemplazarlo en /etc/hosts
            stdin, stdout, stderr = ssh.exec_command('hostname')
            current_system_hostname = stdout.read().decode().strip()
            logger.info(f"Hostname actual del sistema: {current_system_hostname}")

            # Crear un archivo temporal con el contenido modificado
            modified_content = ""
            found_localhost = False

            for line in hosts_content.split('\n'):
                # Comprobar si es la línea con 127.0.1.1
                if line.strip().startswith('127.0.1.1'):
                    found_localhost = True
                    # Reemplazar solo el hostname, manteniendo cualquier otro texto
                    if current_system_hostname in line:
                        modified_line = line.replace(current_system_hostname, new_hostname)
                    else:
                        # Si no encontramos el hostname actual, simplemente añadimos la nueva línea
                        modified_line = f"127.0.1.1\t{new_hostname}"
                    modified_content += modified_line + "\n"
                else:
                    modified_content += line + "\n"

            # Si no encontramos la línea, añadirla al final
            if not found_localhost:
                modified_content += f"127.0.1.1\t{new_hostname}\n"

            # Crear un archivo temporal con el contenido modificado
            temp_file = f"/tmp/hosts.{device_id}"
            logger.info(f"Creando archivo temporal de hosts: {temp_file}")
            stdin, stdout, stderr = ssh.exec_command(f'echo "{modified_content}" > {temp_file}')
            stdout.read()  # Esperar a que termine

            # Mover el archivo temporal a /etc/hosts con sudo
            logger.info("Aplicando cambios a /etc/hosts")
            stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S mv {temp_file} /etc/hosts')
            error = stderr.read().decode()
            if error and "denied" in error.lower():
                logger.error(f"Error al modificar /etc/hosts: {error}")
                return {'success': False, 'message': f'Error al modificar /etc/hosts: Permisos denegados'}

            # Asegurar permisos correctos
            stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S chmod 644 /etc/hosts')
            stdout.read()
            
            # 3. Cambiar hostname en tiempo real - usando diferentes métodos según el dispositivo
            if device_type == "orange" or is_armbian:
                # Método para OrangePi/Armbian
                logger.info("Usando método OrangePi/Armbian para cambiar hostname")
                
                # Algunos sistemas basados en Armbian pueden no tener hostnamectl
                stdin, stdout, stderr = ssh.exec_command('which hostnamectl')
                has_hostnamectl = len(stdout.read().strip()) > 0
                
                if has_hostnamectl:
                    # Intentar con hostnamectl primero
                    stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S hostnamectl set-hostname {new_hostname}')
                    error = stderr.read().decode()
                    if error and "command not found" not in error:
                        logger.warning(f"Error con hostnamectl: {error}")
                
                # Método alternativo que funciona en casi todos los sistemas Linux
                stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S hostname {new_hostname}')
                error = stderr.read().decode()
                if error:
                    logger.warning(f"Error con hostname command: {error}")
                
                # En algunos sistemas puede ser necesario reiniciar ciertos servicios
                stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S systemctl restart systemd-hostnamed || true')
                
            else:
                # Método para Raspberry Pi
                logger.info("Usando método Raspberry Pi para cambiar hostname")
                stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S hostnamectl set-hostname {new_hostname}')
                stdout.read()
            
            # Verificar que el cambio fue exitoso
            logger.info("Verificando cambio de hostname")
            stdin, stdout, stderr = ssh.exec_command('hostname')
            current_hostname = stdout.read().decode().strip()
            logger.info(f"Hostname después del cambio: {current_hostname}")

            if current_hostname == new_hostname:
                # El cambio fue exitoso, programar un reinicio
                logger.info(f"Cambio de hostname exitoso para {ip_address}. Reiniciando el dispositivo...")
                
                # Programar reinicio en 1 minuto para permitir que la respuesta llegue al cliente
                stdin, stdout, stderr = ssh.exec_command(f'echo "{SSH_PASSWORD}" | sudo -S shutdown -r +1 "El sistema se reiniciará en 1 minuto debido al cambio de hostname" &')
                stdout.read()
                
                # Actualizar en la base de datos
                device.name = new_hostname
                db.commit()
                
                # Cerrar la conexión SSH
                ssh.close()
                
                return {
                    'success': True, 
                    'message': f'Hostname cambiado exitosamente a {new_hostname} vía {connection_type}. El dispositivo se reiniciará en 1 minuto.',
                    'old_hostname': device_id,
                    'new_hostname': new_hostname,
                    'reboot': True,
                    'connection_type': connection_type,
                    'device_type': device_type
                }
            else:
                # Error al cambiar el hostname
                ssh.close()
                return {
                    'success': False, 
                    'message': f'El hostname no se actualizó correctamente. Valor actual: {current_hostname}',
                    'reboot': False
                }
        
        except Exception as e:
            logger.error(f"Error al conectar por SSH a {ip_address}: {str(e)}")
            return {'success': False, 'message': f'Error de conexión SSH: {str(e)}'}
        
    finally:
        db.close()