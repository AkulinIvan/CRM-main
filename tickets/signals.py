import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Ticket
from notifications.services import NotificationService
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Ticket)
def handle_ticket_status_change(sender, instance, created, **kwargs):
    if not created and instance.tracker.has_changed('status'):
        if instance.status == Ticket.Status.COMPLETED:
            NotificationService.send_ticket_notification(instance, 'TICKET_COMPLETED')
        elif instance.status == Ticket.Status.CANCELED:
            NotificationService.send_ticket_notification(instance, 'TICKET_CANCELED')

@receiver(pre_save, sender=Ticket)
def check_priority_change(sender, instance, **kwargs):
    if not instance._state.adding and instance.tracker.has_changed('priority'):
        if instance.priority == Ticket.Priority.CRITICAL:
            NotificationService.send_ticket_notification(
                instance, 
                'TICKET_PRIORITY_CHANGED',
                {'priority': instance.get_priority_display()}
            )
            
@receiver(post_save, sender=Ticket)
def handle_ticket_notifications(sender, instance, created, **kwargs):
    if created:
        try:
            from notifications.services import NotificationService
            NotificationService.send_ticket_notification(instance, 'TICKET_CREATED')
            
            # Асинхронная отправка SMS
            from .tasks import send_ticket_sms_notifications
            send_ticket_sms_notifications.delay(instance.id)
        except Exception as e:
            logger.error(f"Error handling ticket notifications: {str(e)}")