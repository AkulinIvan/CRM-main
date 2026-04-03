# asterisk_app/socket_server.py
import socket
import os
import json
import logging
import threading
import sys
import django
from datetime import datetime
from typing import Dict, Any

# Настройка Django
sys.path.append('/path/to/your/project')  # Укажите путь к вашему проекту
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

from django.utils import timezone
from django.conf import settings
from asterisk_app.models import Call, CallEvent

logger = logging.getLogger(__name__)

class AsteriskSocketServer:
    """
    UNIX Socket сервер для приема событий от Asterisk
    """
    
    def __init__(self, socket_path='/tmp/asterisk_crm.sock'):
        self.socket_path = socket_path
        self.server_socket = None
        self.running = False
        self.call_sessions: Dict[str, Dict] = {}  # Хранение сессий звонков
        
    def start(self):
        """Запуск сервера"""
        # Удаляем старый сокет если существует
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(5)
        self.running = True
        
        # Устанавливаем права на сокет
        os.chmod(self.socket_path, 0o777)
        
        logger.info(f"Asterisk Socket Server started on {self.socket_path}")
        
        while self.running:
            try:
                client_socket, _ = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
                
    def stop(self):
        """Остановка сервера"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        logger.info("Asterisk Socket Server stopped")
        
    def handle_client(self, client_socket):
        """Обработка клиентского подключения"""
        try:
            # Получаем данные от Asterisk
            data = client_socket.recv(4096).decode('utf-8')
            if data:
                self.process_asterisk_data(data)
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()
            
    def process_asterisk_data(self, data: str):
        """Обработка данных от Asterisk"""
        try:
            # Парсим данные Asterisk (формат: Event: Newchannel\r\nKey: Value\r\n\r\n)
            event_data = self.parse_asterisk_event(data)
            if event_data:
                self.process_event(event_data)
        except Exception as e:
            logger.error(f"Error processing Asterisk data: {e}")
            
    def parse_asterisk_event(self, data: str) -> Dict[str, Any]:
        """Парсинг AMI события в словарь"""
        event = {}
        lines = data.strip().split('\n')
        
        for line in lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                event[key] = value.strip()
                
        return event
        
    def process_event(self, event: Dict[str, Any]):
        """Обработка события от Asterisk"""
        event_type = event.get('Event')
        if not event_type:
            return
            
        unique_id = event.get('Uniqueid', '')
        channel = event.get('Channel', '')
        
        logger.info(f"Processing event: {event_type} for {unique_id}")
        
        # Обрабатываем различные типы событий
        if event_type == 'Newchannel':
            self.handle_new_channel(event)
        elif event_type == 'Newstate':
            self.handle_new_state(event)
        elif event_type == 'Newcallerid':
            self.handle_new_callerid(event)
        elif event_type == 'Dial':
            self.handle_dial(event)
        elif event_type == 'DialBegin':
            self.handle_dial_begin(event)
        elif event_type == 'DialEnd':
            self.handle_dial_end(event)
        elif event_type == 'Hangup':
            self.handle_hangup(event)
        elif event_type == 'HangupRequest':
            self.handle_hangup_request(event)
        elif event_type == 'Ringing':
            self.handle_ringing(event)
        elif event_type == 'Answer':
            self.handle_answer(event)
        elif event_type == 'VarSet':
            self.handle_var_set(event)
            
    def handle_new_channel(self, event: Dict[str, Any]):
        """Обработка нового канала"""
        unique_id = event.get('Uniqueid')
        channel = event.get('Channel')
        context = event.get('Context')
        exten = event.get('Exten')
        
        # Определяем тип звонка
        call_type = 'incoming' if event.get('CallerIDNum') else 'outgoing'
        
        # Создаем сессию звонка
        self.call_sessions[unique_id] = {
            'unique_id': unique_id,
            'channel': channel,
            'context': context,
            'extension': exten,
            'call_type': call_type,
            'start_time': timezone.now(),
            'events': []
        }
        
        # Создаем запись в БД
        call = Call.objects.create(
            unique_id=unique_id,
            phone=event.get('CallerIDNum', ''),
            caller_id_name=event.get('CallerIDName', ''),
            context=context,
            extension=exten,
            channel=channel,
            call_type=call_type,
            call_status='started',
            call_date=timezone.now()
        )
        
        # Сохраняем ID звонка в сессии
        self.call_sessions[unique_id]['call_id'] = call.id
        
        # Сохраняем событие
        CallEvent.objects.create(
            call=call,
            event_type='Newchannel',
            data=event
        )
        
        logger.info(f"New channel created: {unique_id} - {call.phone}")
        
    def handle_new_callerid(self, event: Dict[str, Any]):
        """Обработка нового CallerID"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                call = Call.objects.get(id=call_id)
                call.phone = event.get('CallerIDNum', call.phone)
                call.caller_id_name = event.get('CallerIDName', '')
                call.save()
                
                CallEvent.objects.create(
                    call=call,
                    event_type='Newcallerid',
                    data=event
                )
                
    def handle_answer(self, event: Dict[str, Any]):
        """Обработка ответа на звонок"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                call = Call.objects.get(id=call_id)
                call.call_status = 'answered'
                call.save()
                
                CallEvent.objects.create(
                    call=call,
                    event_type='Answer',
                    data=event
                )
                
                logger.info(f"Call answered: {unique_id}")
                
    def handle_hangup(self, event: Dict[str, Any]):
        """Обработка отбоя"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                call = Call.objects.get(id=call_id)
                
                # Обновляем длительность
                duration = int(event.get('Duration', 0))
                call.duration = duration
                call.call_status = 'completed'
                
                # Определяем тип звонка если пропущенный
                if duration == 0 and call.call_type == 'incoming':
                    call.call_type = 'missed'
                    
                call.save()
                
                CallEvent.objects.create(
                    call=call,
                    event_type='Hangup',
                    data=event
                )
                
                # Удаляем сессию
                del self.call_sessions[unique_id]
                
                logger.info(f"Call hung up: {unique_id}, duration: {duration}")
                
    def handle_ringing(self, event: Dict[str, Any]):
        """Обработка звонка (ринга)"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                CallEvent.objects.create(
                    call=Call.objects.get(id=call_id),
                    event_type='Ringing',
                    data=event
                )
                
    def handle_dial(self, event: Dict[str, Any]):
        """Обработка набора номера"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                call = Call.objects.get(id=call_id)
                call.destination = event.get('Destination', '')
                call.dst_channel = event.get('DestinationChannel', '')
                call.save()
                
                CallEvent.objects.create(
                    call=call,
                    event_type='Dial',
                    data=event
                )
                
    def handle_new_state(self, event: Dict[str, Any]):
        """Обработка нового состояния канала"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                CallEvent.objects.create(
                    call=Call.objects.get(id=call_id),
                    event_type='Newstate',
                    data=event
                )
                
    def handle_dial_begin(self, event: Dict[str, Any]):
        """Начало набора номера"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                CallEvent.objects.create(
                    call=Call.objects.get(id=call_id),
                    event_type='DialBegin',
                    data=event
                )
                
    def handle_dial_end(self, event: Dict[str, Any]):
        """Конец набора номера"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                CallEvent.objects.create(
                    call=Call.objects.get(id=call_id),
                    event_type='DialEnd',
                    data=event
                )
                
    def handle_hangup_request(self, event: Dict[str, Any]):
        """Запрос на отбой"""
        unique_id = event.get('Uniqueid')
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                CallEvent.objects.create(
                    call=Call.objects.get(id=call_id),
                    event_type='HangupRequest',
                    data=event
                )
                
    def handle_var_set(self, event: Dict[str, Any]):
        """Установка переменной"""
        unique_id = event.get('Uniqueid')
        variable = event.get('Variable', '')
        value = event.get('Value', '')
        
        if unique_id in self.call_sessions:
            call_id = self.call_sessions[unique_id].get('call_id')
            if call_id:
                call = Call.objects.get(id=call_id)
                
                # Сохраняем важные переменные
                if variable == 'RECORDED_FILE':
                    call.recording_path = value
                    call.save()
                elif variable == 'userfield':
                    call.userfield = value
                    call.save()
                elif variable == 'accountcode':
                    call.account_code = value
                    call.save()
                    
                CallEvent.objects.create(
                    call=call,
                    event_type='VarSet',
                    data=event
                )


def run_socket_server():
    """Запуск сервера (для использования в manage.py команде)"""
    server = AsteriskSocketServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        logger.error(f"Server error: {e}")
        server.stop()
        raise


if __name__ == '__main__':
    run_socket_server()