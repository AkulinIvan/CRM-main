# Убедитесь, что этот файл экспортирует Tele2SMSService
from .send_sms import Tele2SMSService

# Если используете заглушку:
from django.conf import settings

if getattr(settings, 'SMS_MOCK_MODE', False):
    from .sms_service import Tele2SMSService
else:
    from .send_sms import Tele2SMSService

__all__ = ['Tele2SMSService']