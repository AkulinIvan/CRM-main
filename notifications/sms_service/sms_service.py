from django.conf import settings
import requests
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

class Tele2SMSService:
    STATUS_MAP = {
        'delivered': 'Доставлено',
        'billed': 'Передано оператору',
        'sending': 'Отправляется',
        'expired': 'Просрочено',
        'undeliverable': 'Не доставлено',
        'rejected': 'Отклонено',
        'unknown': 'Неизвестный статус'
    }
    
    @staticmethod
    def check_sms_status(sms_id):
        """Проверка статуса отправки SMS"""
        if not sms_id:
            return 'Неизвестный идентификатор SMS'
            
        try:
            params = {
                'operation': 'status',
                'login': settings.TELE2_API_LOGIN,
                'password': settings.TELE2_API_PASSWORD,
                'id': sms_id
            }
            
            url = "http://newbsms.tele2.ru/api/send?" + "&".join(
                f"{k}={quote(str(v))}" for k, v in params.items()
            )
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            status_code = response.text.strip().lower()
            return Tele2SMSService.STATUS_MAP.get(status_code, status_code)
            
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error checking SMS status {sms_id}. Error: {str(e)}",
                exc_info=True
            )
            return f"Ошибка проверки: {str(e)}"
        except Exception as e:
            logger.error(
                f"Unexpected error checking SMS {sms_id}. Error: {str(e)}",
                exc_info=True
            )
            return f"Неизвестная ошибка: {str(e)}"