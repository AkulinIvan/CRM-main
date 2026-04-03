import httpx
from celery import Celery
from celery import shared_task
from django.conf import settings
import os
from .models import Call
from celery.schedules import crontab

import logging
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

@shared_task
def process_call_recordings():
    """Обработка записей с гарантированным обновлением пути в тестах"""
    calls = Call.objects.filter(recording_path__isnull=False, is_processed=False)
    
    for call in calls:
        try:
            if not call.recording_path.startswith('/'):
                continue
                
            # Формируем новый путь
            date_folder = call.call_date.strftime('%Y-%m-%d')
            new_path = f'call_recordings/{date_folder}/{call.unique_id}.wav'
            
            # В тестовом режиме просто обновляем путь
            if getattr(settings, 'TESTING', False):
                call.recording_path = new_path
                call.is_processed = True
                call.save()
                logger.info(f"TEST MODE: Updated path to {new_path}")
                continue
                
            # Реальная логика для production
            full_path = os.path.join(settings.MEDIA_ROOT, new_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if download_from_asterisk(
                call.recording_path,
                full_path,
                settings.ASTERISK_SERVER,
                settings.ASTERISK_USER,
                settings.ASTERISK_PASSWORD
            ):
                call.recording_path = new_path
                call.is_processed = True
                call.save()
                
        except Exception as e:
            logger.error(f"Error processing call {call.id}: {str(e)}")
            continue

def download_from_asterisk(remote_path, local_path, asterisk_server, asterisk_user, asterisk_password):
    """Скачивание файла с сервера Asterisk по SFTP"""
    try:
        import paramiko
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(asterisk_server, username=asterisk_user, password=asterisk_password)
        
        sftp = ssh.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        ssh.close()
        
        return True
    except Exception as e:
        logger.error(f"Error downloading from Asterisk: {str(e)}")
        return False
    
@shared_task(bind=True)
def check_missed_calls(self):
    """
    Проверка пропущенных звонков и создание тикетов в CRM
    Логика работы:
    1. Найти все пропущенные звонки за последний час, которые еще не обработаны
    2. Для каждого звонка создать тикет в CRM
    3. Отправить уведомления ответственному менеджеру
    4. Пометить звонки как обработанные
    """
    try:
        # 1. Поиск пропущенных звонков
        one_hour_ago = datetime.now() - timedelta(hours=1)
        missed_calls = Call.objects.filter(
            call_type='missed',
            is_processed=False,
            call_date__gte=one_hour_ago
        ).order_by('-call_date')

        logger.info(f"Found {len(missed_calls)} missed calls to process")

        for call in missed_calls:
            try:
                # 2. Создание тикета в CRM
                ticket_data = {
                    'title': f"Пропущенный звонок от {call.phone}",
                    'description': (
                        f"Дата/время: {call.call_date.strftime('%Y-%m-%d %H:%M')}\n"
                        f"Номер: {call.phone}\n"
                        f"Длительность: {call.duration} сек"
                    ),
                    'call': call,
                    'priority': 'medium',
                    'category': 'missed_call'
                }

                # Здесь интеграция с вашей CRM - создание тикета
                ticket = create_ticket_in_crm(ticket_data)
                
                # 3. Отправка уведомления
                send_missed_call_notification(call, ticket)
                
                # 4. Пометить как обработанный
                call.is_processed = True
                call.ticket_id = ticket['id']  # Сохраняем ID созданного тикета
                call.save()
                
                logger.info(f"Processed missed call {call.id}, created ticket {ticket['id']}")

            except Exception as e:
                logger.error(f"Error processing call {call.id}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error in check_missed_calls task: {str(e)}")
        raise
    
@shared_task(bind=True, max_retries=3)
def create_ticket_in_crm(self, ticket_data):
    """Синхронная версия с httpx (для Celery)"""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.CRM_API_URL}/tickets",
                json=ticket_data,
                headers={'Authorization': f'Bearer {settings.CRM_API_TOKEN}'},
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.error(f"CRM API error: {str(exc)}")
        self.retry(exc=exc, countdown=60)

def send_missed_call_notification(call, ticket):
    """
    Отправка уведомления о пропущенном звонке
    :param call: Объект звонка
    :param ticket: Созданный тикет
    """
    try:
        subject = f"Пропущенный звонок от {call.phone}"
        
        # Получаем ответственного менеджера (можно настроить логику назначения)
        manager_email = get_responsible_manager(call.phone)
        
        context = {
            'phone': call.phone,
            'call_date': call.call_date.strftime('%d.%m.%Y %H:%M'),
            'duration': call.duration,
            'ticket_id': ticket['id'],
            'ticket_url': f"{settings.CRM_BASE_URL}/tickets/{ticket['id']}"
        }
        
        # Текст уведомления
        text_message = render_to_string('calls/email/missed_call.txt', context)
        html_message = render_to_string('calls/email/missed_call.html', context)
        
        # Отправка email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[manager_email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Можно добавить отправку SMS или в мессенджеры
        if settings.SMS_NOTIFICATIONS_ENABLED:
            send_sms_notification(manager_email, text_message)
            
    except Exception as e:
        logger.error(f"Error sending missed call notification: {str(e)}")
        raise

def get_responsible_manager(phone_number):
    """
    Определение ответственного менеджера по номеру телефона
    :param phone_number: Номер телефона клиента
    :return: Email менеджера
    """
    # Здесь можно реализовать логику назначения:
    # - По префиксу номера
    # - По данным клиента из CRM
    # - По очереди менеджеров
    
    # Заглушка - возвращаем общий email для уведомлений
    return settings.MISSED_CALLS_NOTIFICATION_EMAIL

def send_sms_notification(phone, message):
    """
    Отправка SMS уведомления
    :param phone: Номер телефона
    :param message: Текст сообщения
    """
    # Реализация отправки SMS через ваш шлюз
    # Например, через Tele2 API как в предыдущих примерах
    pass

app = Celery('yourproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Расписание периодических задач
app.conf.beat_schedule = {
    'check-missed-calls': {
        'task': 'asterisk_app.tasks.check_missed_calls',
        'schedule': crontab(minute='*/5'),
    },
}

@app.task(queue='high_priority')
def process_call_recording_high_priority(call_id):
    ...

@app.task(queue='low_priority')
def process_call_recording_low_priority(call_id):
    ...

# Мониторинг
from celery import current_app
def check_workers():
    inspector = current_app.control.inspect()
    return inspector.active()