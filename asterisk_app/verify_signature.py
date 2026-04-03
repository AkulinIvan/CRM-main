import hmac
import hashlib
from django.http import HttpResponseForbidden
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


    
def verify_signature(payload, received_signature):
    """
    Проверяет подпись запроса.
    
    :param payload: Тело запроса (bytes)
    :param received_signature: Подпись из заголовка X-Signature
    :return: True если подпись верна, иначе False
    """
    if not received_signature or not hasattr(settings, 'WEBHOOK_SECRET_KEY'):
        return False
        
    # Генерируем ожидаемую подпись
    expected_signature = hmac.new(
        key=settings.WEBHOOK_SECRET_KEY.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Сравниваем подписи безопасным способом (защита от timing attack)
    return hmac.compare_digest(expected_signature, received_signature)