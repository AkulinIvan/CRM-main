# asterisk_app/ami_client.py
import socket
import logging
import threading
import json
from typing import Dict, Any, Callable
from django.conf import settings

logger = logging.getLogger(__name__)

class AMIClient:
    """
    Клиент для подключения к Asterisk Manager Interface
    """
    
    def __init__(self, host='localhost', port=5038, username=None, password=None):
        self.host = host
        self.port = port
        self.username = username or getattr(settings, 'ASTERISK_AMI_USER', '')
        self.password = password or getattr(settings, 'ASTERISK_AMI_PASSWORD', '')
        self.socket = None
        self.connected = False
        self.event_handlers = {}
        
    def connect(self):
        """Подключение к AMI"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Аутентификация
            self.send_action({
                'Action': 'Login',
                'Username': self.username,
                'Secret': self.password
            })
            
            # Получаем ответ
            response = self.receive_response()
            if 'Response: Success' in response:
                self.connected = True
                logger.info(f"Connected to AMI at {self.host}:{self.port}")
                
                # Запускаем поток для прослушивания событий
                self.listen_thread = threading.Thread(target=self.listen_events)
                self.listen_thread.daemon = True
                self.listen_thread.start()
            else:
                logger.error(f"AMI authentication failed: {response}")
                
        except Exception as e:
            logger.error(f"Error connecting to AMI: {e}")
            
    def disconnect(self):
        """Отключение от AMI"""
        if self.connected:
            self.send_action({'Action': 'Logoff'})
            self.connected = False
            if self.socket:
                self.socket.close()
            logger.info("Disconnected from AMI")
            
    def send_action(self, action: Dict[str, Any]):
        """Отправка действия в AMI"""
        if not self.socket:
            raise Exception("Not connected to AMI")
            
        message = '\r\n'.join([f"{k}: {v}" for k, v in action.items()]) + '\r\n\r\n'
        self.socket.send(message.encode())
        
    def receive_response(self) -> str:
        """Получение ответа от AMI"""
        response = ''
        while True:
            chunk = self.socket.recv(4096).decode()
            response += chunk
            if '\r\n\r\n' in response:
                break
        return response
        
    def listen_events(self):
        """Прослушивание событий от AMI"""
        buffer = ''
        while self.connected:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                    
                buffer += data
                
                # Разбираем события
                while '\r\n\r\n' in buffer:
                    event_data, buffer = buffer.split('\r\n\r\n', 1)
                    self.process_event(event_data)
                    
            except Exception as e:
                logger.error(f"Error listening to AMI events: {e}")
                break
                
    def process_event(self, event_data: str):
        """Обработка события AMI"""
        event = {}
        for line in event_data.split('\r\n'):
            if ': ' in line:
                key, value = line.split(': ', 1)
                event[key] = value
                
        event_type = event.get('Event')
        if event_type and event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
                    
        # Отправляем в UNIX Socket
        self.send_to_socket(event)
        
    def send_to_socket(self, event: Dict[str, Any]):
        """Отправка события в UNIX Socket"""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(settings.ASTERISK_SOCKET_PATH)
            sock.send(json.dumps(event).encode())
            sock.close()
        except Exception as e:
            logger.error(f"Error sending event to socket: {e}")
            
    def on(self, event_type: str, handler: Callable):
        """Регистрация обработчика события"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    def originate_call(self, channel: str, extension: str, context: str = 'default',
                      caller_id: str = None, timeout: int = 30000):
        """Инициация исходящего звонка"""
        action = {
            'Action': 'Originate',
            'Channel': channel,
            'Exten': extension,
            'Context': context,
            'Priority': 1,
            'Timeout': timeout,
            'Async': True
        }
        
        if caller_id:
            action['CallerID'] = caller_id
            
        self.send_action(action)
        logger.info(f"Originating call to {extension} via {channel}")
        
    def hangup_call(self, channel: str):
        """Завершение звонка"""
        action = {
            'Action': 'Hangup',
            'Channel': channel
        }
        self.send_action(action)
        logger.info(f"Hanging up channel: {channel}")
        
    def monitor_call(self, channel: str, filename: str = None):
        """Начало записи звонка"""
        if not filename:
            filename = f"recording_{channel}"
            
        action = {
            'Action': 'Monitor',
            'Channel': channel,
            'Mix': 'true',
            'Format': 'wav',
            'Filename': filename
        }
        self.send_action(action)
        logger.info(f"Started monitoring {channel} -> {filename}")
        
    def stop_monitoring(self, channel: str):
        """Остановка записи звонка"""
        action = {
            'Action': 'StopMonitor',
            'Channel': channel
        }
        self.send_action(action)
        logger.info(f"Stopped monitoring {channel}")


# Глобальный экземпляр клиента
ami_client = AMIClient()