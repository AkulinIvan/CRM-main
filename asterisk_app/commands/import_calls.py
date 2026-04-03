from django.core.management.base import BaseCommand
from asterisk_app.models import Call
from tickets.models import Ticket
from datetime import datetime

class Command(BaseCommand):
    help = 'Import calls from Asterisk to CRM'

    def handle(self, *args, **options):
        # Здесь логика импорта звонков из Asterisk
        # Пример:
        call_data = {
            'phone': '79123456789',
            'unique_id': 'ABC123',
            'call_date': datetime.now(),
            'duration': 120,
            'call_type': 'incoming',
            'recording_path': 'call_recordings/ABC123.wav'
        }
        
        # Автоматическая привязка к заявке по номеру телефона
        ticket = Ticket.objects.filter(contact_phone__contains=call_data['phone']).first()
        if ticket:
            call_data['ticket'] = ticket
        
        Call.objects.create(**call_data)
        self.stdout.write(self.style.SUCCESS('Successfully imported call'))