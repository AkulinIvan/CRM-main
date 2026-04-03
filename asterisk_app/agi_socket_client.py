# asterisk_app/agi_socket_client.py
#!/usr/bin/env python3
import socket
import sys
import json
import os
from datetime import datetime

class AGISocketClient:
    """
    AGI скрипт для отправки данных в UNIX Socket
    """
    
    def __init__(self, socket_path='/tmp/asterisk_crm.sock'):
        self.socket_path = socket_path
        
    def send_event(self, event_data: dict):
        """Отправка события в сокет"""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.send(json.dumps(event_data).encode())
            sock.close()
            return True
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return False
            
    def get_agi_vars(self):
        """Получение переменных AGI"""
        vars = {}
        for line in sys.stdin:
            if line.strip() == '':
                break
            if ':' in line:
                key, value = line.split(':', 1)
                vars[key.strip()] = value.strip()
        return vars


if __name__ == '__main__':
    client = AGISocketClient()
    
    # Получаем переменные AGI
    agi_vars = client.get_agi_vars()
    
    # Формируем событие
    event = {
        'Event': 'AGI',
        'Uniqueid': agi_vars.get('agi_uniqueid', ''),
        'Channel': agi_vars.get('agi_channel', ''),
        'CallerID': agi_vars.get('agi_callerid', ''),
        'Extension': agi_vars.get('agi_extension', ''),
        'Context': agi_vars.get('agi_context', ''),
        'Priority': agi_vars.get('agi_priority', ''),
        'Timestamp': datetime.now().isoformat()
    }
    
    # Отправляем событие
    client.send_event(event)