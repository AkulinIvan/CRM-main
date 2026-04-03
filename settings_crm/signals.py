from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import SystemSettings

User = get_user_model()

@receiver(post_save, sender=User)
def check_password_expiration(sender, instance, **kwargs):
    if not instance.is_superuser:
        settings = SystemSettings.get_settings()
        if settings.password_expiration_days > 0:
            expiration_date = instance.last_password_change + timezone.timedelta(days=settings.password_expiration_days)
            if timezone.now() > expiration_date:
                instance.set_unusable_password()
                instance.save()
                # Здесь можно добавить отправку уведомления пользователю о том, что его пароль истек
                raise ValidationError('Ваш пароль истек. Пожалуйста, смените его.')