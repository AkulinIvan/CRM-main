from django.http import HttpResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin
from .models import SystemSettings

class MaintenanceModeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        settings = SystemSettings.get_settings()
        
        # Исключения для режима обслуживания
        excluded_paths = [
            '/admin/',
            '/accounts/login/',
            '/accounts/logout/',
        ]
        
        if (settings.maintenance_mode and 
            not any(request.path.startswith(path) for path in excluded_paths) and
            not (hasattr(request, 'user') and request.user.is_authenticated and request.user.is_admin)):
            return render(request, 'settings/maintenance.html', status=503)
        
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        settings = SystemSettings.get_settings()  # Получаем настройки
        
        # Базовые заголовки безопасности
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # CSP (Content Security Policy)
        if hasattr(settings, 'enable_csp') and settings.enable_csp:  # Проверяем наличие атрибута
            csp_policy = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; font-src 'self' https://cdn.jsdelivr.net;"
            response['Content-Security-Policy'] = csp_policy
        
        return response