import logging

class UserContextFilter(logging.Filter):
    """
    Добавляет информацию о пользователе и IP-адресе в лог
    """
    def filter(self, record):
        from django.contrib.auth.models import AnonymousUser
        
        request = getattr(record, 'request', None)
        if request:
            record.ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
            user = getattr(request, 'user', None)
            if user and not isinstance(user, AnonymousUser):
                record.user = f"{user.username} ({user.get_role_display()})"
            else:
                record.user = 'anonymous'
        else:
            record.ip = '0.0.0.0'
            record.user = 'system'
            
        return True