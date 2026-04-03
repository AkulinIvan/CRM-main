# asterisk_app/management/commands/run_socket_server.py
from django.core.management.base import BaseCommand
from asterisk_app.socket_server import run_socket_server

class Command(BaseCommand):
    help = 'Run Asterisk UNIX Socket Server'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--socket-path',
            type=str,
            default='/tmp/asterisk_crm.sock',
            help='UNIX socket path'
        )
        
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Asterisk Socket Server...'))
        run_socket_server()