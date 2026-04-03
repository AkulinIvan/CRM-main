import psutil
import socket
import logging
from django.core.management.base import BaseCommand
import os

logger = logging.getLogger(__name__)

class SocketMonitor:
    """Мониторинг состояния сокета"""
    
    def __init__(self, socket_path='/tmp/asterisk_crm.sock'):
        self.socket_path = socket_path
        
    def is_socket_exists(self) -> bool:
        """Проверка существования сокета"""
        return os.path.exists(self.socket_path)
        
    def is_socket_active(self) -> bool:
        """Проверка активности сокета"""
        if not self.is_socket_exists():
            return False
            
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.close()
            return True
        except:
            return False
            
    def get_socket_permissions(self) -> str:
        """Получение прав доступа к сокету"""
        if self.is_socket_exists():
            return oct(os.stat(self.socket_path).st_mode)[-3:]
        return None
        
    def check_socket_health(self) -> dict:
        """Проверка здоровья сокета"""
        return {
            'exists': self.is_socket_exists(),
            'active': self.is_socket_active(),
            'permissions': self.get_socket_permissions(),
            'path': self.socket_path
        }