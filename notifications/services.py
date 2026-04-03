from django.conf import settings
from notifications.models import PushNotification
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_ticket_notification(ticket, notification_type, extra_context=None):
        try:
            """Отправка уведомления о заявке с сохранением в базу"""
            if extra_context is None:
                extra_context = {}

            context = {
                'id': ticket.id,
                'title': ticket.title,
                'status': ticket.get_status_display(),
                **extra_context
            }

            # Получаем конфиг уведомления
            if notification_type not in settings.NOTIFICATION_TYPES:
                logger.warning(f"Unknown notification type: {notification_type}")
                return False

            # Определяем получателей
            recipients = NotificationService._get_recipients(ticket, notification_type)


            for user in recipients:
                NotificationService._send_user_notification(
                    user, ticket, notification_type, context
                )
                
            return True
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}", exc_info=True)
            return False
                
    
    @staticmethod
    def _get_recipients(ticket, notification_type):
        """Определение получателей по типу уведомления"""
        recipients = []
        
        if notification_type == 'TICKET_CREATED':
            if ticket.executor:
                recipients.append(ticket.executor)
            if ticket.master:
                recipients.append(ticket.master)
        elif notification_type == 'TICKET_UPDATED':
            if ticket.executor:
                recipients.append(ticket.executor)
            if ticket.master:
                recipients.append(ticket.master)
            if ticket.created_by:
                recipients.append(ticket.created_by)
        elif notification_type == 'TICKET_COMPLETED':
            if ticket.created_by:
                recipients.append(ticket.created_by)
            if ticket.master:
                recipients.append(ticket.master)
        elif notification_type == 'TICKET_ASSIGNED':
            if ticket.executor:
                recipients.append(ticket.executor)
        
        return list(set(recipients))
    
    @staticmethod
    def _send_sms_notification(ticket, user, notification_type, context):
        """Отправка SMS и сохранение в лог"""
        from .sms_service import Tele2SMSService
        
        # Получаем шаблон SMS
        sms_template = settings.SMS_TEMPLATES.get(user.profile.user_type)
        if not sms_template:
            return
            
        # Формируем сообщение
        message = sms_template.format(**context)
        
        # Отправляем SMS
        result = Tele2SMSService.send_sms(
            phone=user.phone,
            message=message,
            recipient_type=user.profile.user_type,
            ticket_id=ticket.id
        )
        
        # Сохраняем в лог (уже делается в Tele2SMSService)
    
    @staticmethod
    def _send_push_notification(ticket, user, notification_type, context, notification_config):
        """Отправка Push-уведомления и сохранение в базу"""
        for subscription in user.push_subscriptions.all():
            try:
                # Формируем данные уведомления
                notification_data = {
                    'title': notification_config['title'],
                    **notification_config['options']
                }
                
                # Заменяем плейсхолдеры
                for key, value in context.items():
                    if isinstance(notification_data['body'], str):
                        notification_data['body'] = notification_data['body'].replace(f'{{{key}}}', str(value))
                
                # Отправляем уведомление
                success = subscription.send_notification(
                    notification_type,
                    context
                )
                
                # Сохраняем в базу
                PushNotification.objects.create(
                    ticket=ticket,
                    recipient=user,
                    subscription=subscription,
                    notification_type=notification_type.lower(),
                    status='delivered' if success else 'failed',
                    title=notification_data['title'],
                    body=notification_data['body'],
                    data=context
                )
                
            except Exception as e:
                logger.error(f"Error sending push notification: {str(e)}")