from django.core.management.base import BaseCommand
from asterisk_app.models import Call
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Imports call data from Asterisk'

    def add_arguments(self, parser):
        parser.add_argument('--phone', type=str, required=True)
        parser.add_argument('--unique_id', type=str, required=True)
        parser.add_argument('--call_date', type=str, required=True)
        parser.add_argument('--duration', type=int, required=True)
        parser.add_argument('--call_type', type=str, required=True)

    def handle(self, *args, **options):
        phone = options['phone']
        unique_id = options['unique_id']
        call_date = options['call_date']
        duration = options['duration']
        call_type = options['call_type']

        # Проверяем, существует ли уже такой звонок
        if Call.objects.filter(unique_id=unique_id).exists():
            logger.warning(f'Duplicate call with unique_id {unique_id}')
            return

        # Создаем новый звонок
        Call.objects.create(
            phone=phone,
            unique_id=unique_id,
            call_date=call_date,
            duration=duration,
            call_type=call_type
        )

        logger.info(f'Successfully imported call from {phone}')