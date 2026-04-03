from django.core.management.base import BaseCommand
from accounts.models import Specialization

class Command(BaseCommand):
    help = 'Create initial specializations'
    
    def handle(self, *args, **options):
        specializations = [
            {'name': 'Сантехник', 'code': 'plumber'},
            {'name': 'Электрик', 'code': 'electrician'},
            {'name': 'Плотник', 'code': 'carpenter'},
            {'name': 'Уборщица', 'code': 'cleaner'},
            {'name': 'Дворник', 'code': 'janitor'},
            {'name': 'Благоустройство', 'code': 'landscaping'},
            {'name': 'Сети', 'code': 'network'},
            {'name': 'Дератизация', 'code': 'deratization'},
            {'name': 'Дезинфекция', 'code': 'disinfection'},
            {'name': 'Дезинсекция', 'code': 'disinsection'},
            {'name': 'Проверка счетчиков', 'code': 'meter_checker'},
            {'name': 'Осмотр СОИ', 'code': 'soi_inspector'},
            {'name': 'Паспортный стол', 'code': 'passport'},
            {'name': 'Домофон', 'code': 'intercom'},
            {'name': 'Инженер', 'code': 'engineer'},
            {'name': 'Другое', 'code': 'other'}
        ]
        
        for spec_data in specializations:
            Specialization.objects.get_or_create(
                code=spec_data['code'],
                defaults={'name': spec_data['name'], 'is_active': True}
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully created specializations'))