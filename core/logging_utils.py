import logging
import json
from datetime import datetime
from django.conf import settings
from django.utils import timezone

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.propagate = False

    def log(self, level, event_type, **kwargs):
        """Log structured event"""
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'level': level.upper(),
            **kwargs
        }
        
        if settings.DEBUG:
            log_data['environment'] = 'development'
        
        getattr(self.logger, level.lower())(json.dumps(log_data))

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        try:
            message = json.loads(record.getMessage())
        except json.JSONDecodeError:
            message = {'message': record.getMessage()}
            
        return json.dumps({
            'timestamp': datetime.isoformat() + 'Z',
            'level': record.levelname,
            **message
        })

class AuditLog:
    _logger = logging.getLogger('audit')

    @classmethod
    def log(cls, action, target, status, details, request=None):
        user = getattr(request, 'user', None)
        
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'event_type': 'audit_event',
            'action': action,
            'target': target,
            'status': status,
            'details': details,
            'user': user.username if user and hasattr(user, 'username') else 'anonymous',
        }

        try:
            cls._logger.info(json.dumps(log_data))
        except Exception as e:
            # Фоллбек на случай ошибок логирования
            print(f"Audit log failed: {e}\nData: {log_data}")

    @classmethod
    def setup_logger(cls):
        if not cls._logger.handlers:
            handler = logging.FileHandler('audit.log')
            formatter = logging.Formatter('%(message)s')  # Упрощенный формат
            handler.setFormatter(formatter)
            cls._logger.addHandler(handler)
            cls._logger.setLevel(logging.INFO)

# Инициализация при загрузке модуля
AuditLog.setup_logger()

class NotificationLog:
    _logger = StructuredLogger('notifications')

    @classmethod
    def log(cls, notification_type, sender, recipient, status, details=''):
        """
        Log notification event
        
        Args:
            notification_type: Type of notification
            sender: Sender identifier
            recipient: Recipient identifier
            status: Delivery status
            details: Additional details
        """
        log_level = 'error' if status.lower() == 'failed' else 'info'
        cls._logger.log(
            log_level,
            'notification_event',
            notification_type=notification_type,
            sender=sender,
            recipient=recipient,
            status=status,
            details=details
        )