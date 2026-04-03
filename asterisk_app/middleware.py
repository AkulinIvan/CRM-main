from django.http import HttpResponseForbidden
from django.conf import settings
import logging
from .verify_signature import verify_signature
logger = logging.getLogger(__name__)

class AsteriskIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.path.startswith('/api/calls/'):
            remote_ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')
            if remote_ip not in settings.ALLOWED_ASTERISK_IPS:
                logger.warning(f"Blocked unauthorized IP: {remote_ip}")
                return HttpResponseForbidden("IP not allowed")
            
            # Проверка подписи запроса
            signature = request.headers.get('X-Signature')
            if not verify_signature(request.body, signature):
                logger.warning(f"Invalid signature from IP: {remote_ip}")
                return HttpResponseForbidden("Invalid signature")
        
        return self.get_response(request)