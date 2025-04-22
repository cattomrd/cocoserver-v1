# /utils/hostname_changer.py
import asyncio
import logging
from sqlalchemy.orm import Session
import paramiko
import os
from io import StringIO

from models import models
from models.database import SessionLocal

logger = logging.getLogger(__name__)

# Configuración SSH
ssh_password = os.environ.get('SSH_PASSWORD')
ssh_user= os.environ.get('SSH_USER')
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '/path/to/ssh/key')  # Ruta a la clave SSH privada
SSH_USER = os.environ.get('SSH_USER')  # Usuario SSH predeterminado
SSH_PORT = int(os.environ.get('SSH_PORT', 22))  # Puerto SSH predeterminado
SSH_PASSWORD = os.environ.get('SSH_PASSWORD', '!@Erod800')  # Contraseña SSH (si no usas clave)

async def validate_ssh_credentials(device_id):
    """
    Verifica que se tienen las credenciales SSH necesarias para un dispositivo
    Intenta primero con WiFi, si falla intenta con LAN
    
    Args:
        device_id (str): ID del dispositivo
        
    Returns:
        dict: Resultado de la validación
    """
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
                stdin, stdout, stderr = ssh.exec_command('echo "%s" | sudo -S echo "OK"' % SSH_PASSWORD)
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
    Cambia el hostname de un dispositivo Raspberry Pi
    Intenta primero con WiFi, si falla intenta con LAN
    
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
            
            # Comandos para cambiar el hostname
            # 1. Cambiar en /etc/hostname
            stdin, stdout, stderr = ssh.exec_command(f'echo "{new_hostname}" | sudo tee /etc/hostname')
            stdout.read()
            
            # 2. Leer el contenido actual de /etc/hosts para modificarlo correctamente
            stdin, stdout, stderr = ssh.exec_command('cat /etc/hosts')
            hosts_content = stdout.read().decode()

            # Crear un archivo temporal con el contenido modificado
            modified_content = ""
            found_localhost = False

            for line in hosts_content.split('\n'):
                # Comprobar si es la línea con 127.0.1.1
                if line.strip().startswith('127.0.1.1'):
                    found_localhost = True
                    modified_content += f"127.0.1.1\t{new_hostname}\n"
                else:
                    modified_content += line + "\n"

            # Si no encontramos la línea, añadirla al final
            if not found_localhost:
                modified_content += f"127.0.1.1\t{new_hostname}\n"

            # Crear un archivo temporal con el contenido modificado
            temp_file = f"/tmp/hosts.{device_id}"
            stdin, stdout, stderr = ssh.exec_command(f'echo "{modified_content}" > {temp_file}')
            stdout.read()  # Esperar a que termine

            # Mover el archivo temporal a /etc/hosts
            stdin, stdout, stderr = ssh.exec_command(f'sudo mv {temp_file} /etc/hosts')
            stdout.read()

            # Asegurar permisos correctos
            stdin, stdout, stderr = ssh.exec_command('sudo chmod 644 /etc/hosts')
            stdout.read()
            
            # 3. Cambiar hostname en tiempo real
            stdin, stdout, stderr = ssh.exec_command(f'sudo hostnamectl set-hostname {new_hostname}')
            stdout.read()
            
            # Verificar que el cambio fue exitoso antes de reiniciar
            stdin, stdout, stderr = ssh.exec_command('hostname')
            current_hostname = stdout.read().decode().strip()

            if current_hostname == new_hostname:
                # El cambio fue exitoso, programar un reinicio
                logger.info(f"Cambio de hostname exitoso para {ip_address}. Reiniciando el dispositivo...")
                
                # Programar reinicio en 1 minuto para permitir que la respuesta llegue al cliente
                stdin, stdout, stderr = ssh.exec_command('sudo shutdown -r +1 "El sistema se reiniciará en 1 minuto debido al cambio de hostname" &')
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
                    'connection_type': connection_type
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