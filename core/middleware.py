import logging
from django.conf import settings

logger = logging.getLogger('django.request')

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Пропускаем статические файлы и медиа
        if any(path in request.path for path in ['/static/', '/media/']):
            return self.get_response(request)
            
        response = self.get_response(request)
        
        # Логируем только если путь не в исключениях
        if not any(path in request.path for path in settings.LOGGING_EXCLUDE_PATHS):
            logger.info(
                f"{request.method} {request.path} - {response.status_code}",
                extra={
                    'request': request,
                    'status_code': response.status_code,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                }
            )
            
        return response
    
