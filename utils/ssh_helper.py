# app/utils/ssh_helper.py
# Módulo auxiliar para manejar conexiones SSH a los dispositivos

import paramiko
import logging
import os
import time

# Configuración del logger
logger = logging.getLogger(__name__)

# Obtener variables de entorno para las credenciales SSH
SSH_USERNAME = os.environ.get('SSH_USER')
SSH_PASSWORD = os.environ.get('SSH_PASS')
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH')  # Ruta a la clave privada (opcional)
SSH_PORT = int(os.environ.get('SSH_PORT', '22'))
SSH_TIMEOUT = int(os.environ.get('SSH_TIMEOUT', '10'))  # 10 segundos de timeout por defecto

# Verificar si las variables críticas están definidas
if not SSH_USERNAME:
    logger.warning("SSH_USER no está definido en las variables de entorno.")
    SSH_USERNAME = 'pi'  # Default para Raspberry Pi
    
if not SSH_PASSWORD:
    logger.warning("SSH_PASSWORD no está definido en las variables de entorno.")

def get_ssh_connection(host, port=None, username=None, password=None, key_path=None, timeout=None):
    """
    Establece una conexión SSH con el dispositivo especificado.
    
    Args:
        host (str): Dirección IP o hostname del dispositivo
        port (int, optional): Puerto SSH. Por defecto usa SSH_PORT.
        username (str, optional): Nombre de usuario para SSH. Por defecto usa SSH_USERNAME.
        password (str, optional): Contraseña para SSH. Por defecto usa SSH_PASSWORD.
        key_path (str, optional): Ruta a la clave privada SSH. Por defecto usa SSH_KEY_PATH.
        timeout (int, optional): Tiempo de espera para la conexión en segundos. Por defecto usa SSH_TIMEOUT.
    
    Returns:
        paramiko.SSHClient: Cliente SSH conectado
        
    Raises:
        paramiko.AuthenticationException: Si la autenticación falla
        paramiko.SSHException: Si hay un error en la conexión SSH
        socket.error: Si hay un error de conexión de socket
    """
    try:
        # Usar valores predeterminados si no se proporcionan específicos
        port = port or SSH_PORT
        username = username or SSH_USERNAME
        password = password or SSH_PASSWORD
        key_path = key_path or SSH_KEY_PATH
        timeout = timeout or SSH_TIMEOUT
        
        # Crear cliente SSH
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Opciones de conexión
        connect_kwargs = {
            'hostname': host,
            'port': port,
            'username': username,
            'timeout': timeout
        }
        
        # Usar clave SSH si está disponible
        if key_path and os.path.exists(key_path):
            connect_kwargs['key_filename'] = key_path
            logger.info(f"Conectando por SSH a {host} usando clave privada en {key_path}")
        elif password:
            connect_kwargs['password'] = password
            logger.info(f"Conectando por SSH a {host} usando contraseña")
        else:
            logger.error("No se proporcionó contraseña ni clave SSH para la conexión")
            raise ValueError("Se requiere contraseña o clave SSH para la conexión")
        
        # Intentar conectar
        client.connect(**connect_kwargs)
        logger.info(f"Conexión SSH establecida con {host}")
        
        return client
    
    except paramiko.AuthenticationException as e:
        logger.error(f"Error de autenticación SSH a {host}: {str(e)}")
        raise
    except paramiko.SSHException as e:
        logger.error(f"Error de SSH a {host}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error al conectar por SSH a {host}: {str(e)}")
        raise

def execute_ssh_command(host, command, capture_output=True):
    """
    Ejecuta un comando SSH en el dispositivo remoto y devuelve el resultado.
    
    Args:
        host (str): Dirección IP o hostname del dispositivo
        command (str): Comando a ejecutar
        capture_output (bool, optional): Si se debe capturar la salida. Por defecto es True.
    
    Returns:
        dict: Diccionario con el resultado del comando, incluyendo:
            - success (bool): Si el comando se ejecutó correctamente
            - exit_code (int): Código de salida del comando
            - stdout (str): Salida estándar del comando (si capture_output es True)
            - stderr (str): Salida de error del comando (si capture_output es True)
    """
    client = None
    try:
        # Establecer conexión SSH
        client = get_ssh_connection(host)
        
        # Ejecutar comando
        logger.info(f"Ejecutando comando SSH en {host}: {command}")
        stdin, stdout, stderr = client.exec_command(command)
        
        # Esperar a que el comando termine y obtener código de salida
        exit_status = stdout.channel.recv_exit_status()
        
        result = {
            'success': exit_status == 0,
            'exit_code': exit_status
        }
        
        # Capturar salida si se solicita
        if capture_output:
            result['stdout'] = stdout.read().decode().strip()
            result['stderr'] = stderr.read().decode().strip()
            
        return result
    
    except Exception as e:
        logger.error(f"Error al ejecutar comando SSH en {host}: {str(e)}")
        return {
            'success': False,
            'exit_code': -1,
            'error': str(e)
        }
    finally:
        # Cerrar la conexión SSH
        if client:
            client.close()