import logging
from notifications.models import SmsLog

logger = logging.getLogger(__name__)

class Tele2SMSService:
    """Заглушка для реального SMS сервиса Tele2"""
    
    @staticmethod
    def send_sms(phone, message, recipient_type, ticket_id):
        """Имитация отправки SMS"""
        try:
            logger.info(f"Mock SMS sent to {recipient_type} {phone}. Message: {message[:50]}...")
            
            # Создаем запись в логе как будто SMS отправлено успешно
            SmsLog.objects.create(
                ticket_id=ticket_id,
                recipient_type=recipient_type,
                phone=phone,
                message=message,
                sms_id=f"mock_{ticket_id}_{recipient_type}",
                status='delivered',  # Имитируем успешную доставку
                sms_type='ticket_created'
            )
            
            return {
                'status': 'success',
                'code': f"mock_{ticket_id}_{recipient_type}",
                'message': 'Mock SMS отправлено (режим заглушки)'
            }
            
        except Exception as e:
            logger.error(f"Mock SMS error: {str(e)}")
            return {
                'status': 'error',
                'message': f"Mock SMS ошибка: {str(e)}"
            }

    @staticmethod
    def check_sms_status(sms_id):
        """Имитация проверки статуса SMS"""
        return 'Доставлено (mock)'



# import requests
# import logging
# from django.conf import settings
# from urllib.parse import quote
# from notifications.models import SmsLog

# logger = logging.getLogger(__name__)

# class Tele2SMSService:
#     MAX_SMS_LENGTH = 800  # Максимальная длина SMS сообщения
    
#     @staticmethod
#     def send_sms(phone, message, recipient_type, ticket_id):
#         """
#         Отправка SMS через Tele2 API
#         :param phone: Номер телефона (формат: 79123456789)
#         :param message: Текст сообщения (макс 800 символов)
#         :param recipient_type: Тип получателя (worker, master, resident)
#         :param ticket_id: ID связанной заявки
#         :return: dict {status: 'success'|'error', code: str, message: str}
#         """
#         if len(message) > Tele2SMSService.MAX_SMS_LENGTH:
#             message = message[:Tele2SMSService.MAX_SMS_LENGTH-3] + "..."
        
#         try:
#             # Безопасное формирование URL
#             params = {
#                 'operation': 'send',
#                 'login': settings.TELE2_API_LOGIN,
#                 'password': settings.TELE2_API_PASSWORD,
#                 'msisdn': phone,
#                 'shortcode': settings.TELE2_SENDER,
#                 'text': message
#             }
            
#             url = "http://newbsms.tele2.ru/api/send?" + "&".join(
#                 f"{k}={quote(str(v))}" for k, v in params.items()
#             )
            
#             response = requests.get(url, timeout=10)
#             response.raise_for_status()
            
#             sms_id = response.text.strip() if response.text else None
#             status = 'sent' if response.ok else 'failed'
            
#             # Логируем отправку
#             SmsLog.objects.create(
#                 ticket_id=ticket_id,
#                 recipient_type=recipient_type,
#                 phone=phone,
#                 message=message,
#                 sms_id=sms_id,
#                 status=status
#             )
            
#             logger.info(
#                 f"SMS sent to {recipient_type} {phone} for ticket {ticket_id}. "
#                 f"SMS ID: {sms_id}, Status: {status}"
#             )
            
#             return {
#                 'status': 'success',
#                 'code': sms_id,
#                 'message': 'SMS отправлено'
#             }
#         except requests.exceptions.ConnectTimeout:
#             logger.error(f"Connection timeout to Tele2 SMS service for {recipient_type} {phone}")
#             return {
#                 'status': 'error',
#                 'message': 'SMS service unavailable (timeout)'
#             }
#         except requests.exceptions.RequestException as e:
#             logger.error(
#                 f"SMS sending failed to {recipient_type} {phone}. "
#                 f"Error: {str(e)}",
#                 exc_info=True
#             )
#             return {
#                 'status': 'error',
#                 'message': f"Ошибка связи с SMS сервисом: {str(e)}"
#             }
#         except Exception as e:
#             logger.error(
#                 f"Unexpected error sending SMS to {recipient_type} {phone}. "
#                 f"Error: {str(e)}",
#                 exc_info=True
#             )
#             return {
#                 'status': 'error',
#                 'message': f"Неизвестная ошибка: {str(e)}"
#             }