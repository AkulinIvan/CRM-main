from django.utils import timezone
from django.conf import settings
from django.db import models

import json

class PushNotification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('sent', 'Отправлено'),
        ('delivered', 'Доставлено'),
        ('read', 'Прочитано'),
        ('failed', 'Ошибка')
    ]
    
    TYPES = [
        ('ticket_created', 'Создание заявки'),
        ('ticket_updated', 'Обновление заявки'),
        ('ticket_completed', 'Завершение заявки'),
        ('ticket_assigned', 'Назначение заявки'),
        ('other', 'Другое')
    ]
    
    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='push_notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subscription = models.ForeignKey('PushSubscription', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Push уведомление'
        verbose_name_plural = 'Push уведомления'
    
    def mark_as_read(self):
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Push {self.get_notification_type_display()} для {self.recipient.username}"

class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500)
    keys = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Подписка {self.user.username}"

    def send_notification(self, notification_type, context=None):
        from django.conf import settings
        from pywebpush import webpush, WebPushException
        from urllib.parse import urlparse
        
        if context is None:
            context = {}
            
        notification_config = settings.NOTIFICATION_TYPES.get(notification_type, {})
        if not notification_config:
            return False
            
        try:
            # Формируем данные уведомления
            notification_data = {
                'title': notification_config['title'],
                **notification_config['options']
            }
            
            # Заменяем плейсхолдеры в тексте
            for key, value in context.items():
                if isinstance(notification_data['body'], str):
                    notification_data['body'] = notification_data['body'].replace(f'{{{key}}}', str(value))
            
            # Отправляем уведомление
            webpush(
                subscription_info={
                    "endpoint": self.endpoint,
                    "keys": self.keys
                },
                data=json.dumps(notification_data),
                vapid_private_key=settings.WEBPUSH_SETTINGS['VAPID_PRIVATE_KEY'],
                vapid_claims={
                    "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}",
                }
            )
            return True
        except WebPushException as ex:
            if ex.response.status_code == 410:
                # Подписка больше не действительна - удаляем
                self.delete()
            return False
        
class SmsLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('sent', 'Отправлено'),
        ('delivered', 'Доставлено'),
        ('failed', 'Не доставлено'),
        ('read', 'Прочитано')
    ]
    
    TYPES = [
        ('ticket_created', 'Создание заявки'),
        ('ticket_updated', 'Обновление заявки'),
        ('ticket_completed', 'Завершение заявки'),
        ('ticket_assigned', 'Назначение заявки'),
        ('other', 'Другое')
    ]
    
    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='sms_logs')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    recipient_type = models.CharField(max_length=20)  # master, worker, resident
    phone = models.CharField(max_length=20)
    message = models.TextField()
    sms_id = models.CharField(max_length=100, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sms_type = models.CharField(max_length=20, choices=TYPES, default='ticket_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SMS лог'
        verbose_name_plural = 'SMS логи'
    
    def __str__(self):
        return f"SMS {self.get_sms_type_display()} для {self.phone} (Статус: {self.get_status_display()})"