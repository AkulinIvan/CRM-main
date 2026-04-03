# asterisk_app/management/commands/run_ami_client.py
from django.core.management.base import BaseCommand
from asterisk_app.ami_client import ami_client
import time
import signal
import sys

class Command(BaseCommand):
    help = 'Run Asterisk AMI Client'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            default='localhost',
            help='AMI host'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=5038,
            help='AMI port'
        )
        
    def handle(self, *args, **options):
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('Shutting down...'))
            ami_client.disconnect()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Настраиваем обработчики событий
        def on_hangup(event):
            self.stdout.write(f"Call hung up: {event.get('Uniqueid')}")
            
        def on_answer(event):
            self.stdout.write(f"Call answered: {event.get('Uniqueid')}")
            
        ami_client.on('Hangup', on_hangup)
        ami_client.on('Answer', on_answer)
        
        # Подключаемся
        ami_client.host = options['host']
        ami_client.port = options['port']
        ami_client.connect()
        
        self.stdout.write(self.style.SUCCESS(f'AMI Client connected to {options["host"]}:{options["port"]}'))
        
        # Держим соединение
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            ami_client.disconnect()