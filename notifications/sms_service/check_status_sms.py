from django.core.management.base import BaseCommand
from notifications.sms_service.send_sms import Tele2SMSService
from models import SmsLog

class Command(BaseCommand):
    help = 'Check delivery status of sent SMS messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry checking failed messages'
        )
        
    def handle(self, *args, **options):
        status_filter = ['sent', 'pending']
        if options['retry_failed']:
            status_filter.append('failed')
            
        logs = SmsLog.objects.filter(status__in=status_filter)
        
        for log in logs:
            try:
                status = Tele2SMSService.check_sms_status(log.sms_id)
                if status == 'Доставлено':
                    log.status = 'delivered'
                elif status in ['Не доставлено', 'Просрочено', 'Отклонено']:
                    log.status = 'failed'
                else:
                    continue  # сохраняем текущий статус если он промежуточный
                    
                log.save()
                self.stdout.write(f"SMS {log.sms_id} status: {status}")
            except Exception as e:
                self.stderr.write(f"Error checking SMS {log.sms_id}: {str(e)}")