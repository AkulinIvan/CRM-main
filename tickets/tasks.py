from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from .models import Ticket
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_ticket_sms_notifications(self, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        return ticket.send_notification_sms()
    except ObjectDoesNotExist as e:
        logger.error(f"Ticket {ticket_id} does not exist: {str(e)}")
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        logger.error(f"Error sending SMS for ticket {ticket_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)