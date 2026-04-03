from django.utils import timezone
from .models import SystemSettings

def system_settings(request):
    try:
        settings = SystemSettings.get_settings()
        return {
            'system_settings': settings,
            'current_date': timezone.now(),
        }
    except:
        return {
            'system_settings': None,
            'current_date': timezone.now(),
        }