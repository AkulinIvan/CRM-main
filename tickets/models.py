from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from notifications.sms_service.send_sms import Tele2SMSService

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from settings_crm.utils import validate_file_extension, validate_file_size
from core.logging_utils import AuditLog
from notifications.services import NotificationService
from company.models import ManagementCompany



class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', _('Новая')
        ASSIGNED = 'assigned', _('Назначена')
        IN_PROGRESS = 'in_progress', _('В работе')
        COMPLETED = 'completed', _('Выполнена')
        CANCELED = 'canceled', _('Отменена')

    class Priority(models.TextChoices):
        LOW = 'low', _('Низкий')
        MEDIUM = 'medium', _('Средний')
        HIGH = 'high', _('Высокий')
        CRITICAL = 'critical', _('Критический')

    title = models.CharField(_('Название'), max_length=200)
    description = models.TextField(_('Описание'))
    status = models.CharField(
        _('Статус'),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )
    priority = models.CharField(
        _('Приоритет'),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tickets',
        verbose_name=_('Создатель')
    )
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_('Исполнитель')
    )
    master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='master_tickets',
        # limit_choices_to={'role': User.Role.MASTER},
        verbose_name=_('Мастер участка')
    )
    management_company = models.ForeignKey(
        ManagementCompany,
        on_delete=models.CASCADE,
        default=None,
        related_name='tickets',
        verbose_name=_('Управляющая компания')
    )
    address = models.CharField(_('Адрес'), max_length=300, default='')
    
    specialization = models.ForeignKey(
        'Specialization',
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name='Специализация',
        null=False
    )
    files = models.FileField(
        _('Файлы'),
        upload_to='ticket_files/',
        blank=True,
        validators=[validate_file_extension, validate_file_size]
    )
    class Meta:
        verbose_name = _('Заявка')
        verbose_name_plural = _('Заявки')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def get_specialization_display(self):
        return self.specialization.name if self.specialization else 'Не указана'
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('tickets:detail_ticket', args=[str(self.id)])

    @property
    def is_new(self):
        return self.status == self.Status.NEW

    @property
    def is_assigned(self):
        return self.status == self.Status.ASSIGNED
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        action = 'create' if is_new else 'update'
        
        # Определяем, изменился ли исполнитель
        if not is_new:
            old_ticket = Ticket.objects.get(pk=self.pk)
            executor_changed = old_ticket.executor != self.executor
            if executor_changed:
                self._executor_changed = True
                self._old_executor = old_ticket.executor
        else:
            executor_changed = False
            
        
        with transaction.atomic():
            super().save(*args, **kwargs)
            
            # Логируем действие
            AuditLog.log(
                action=f'ticket_{action}',
                target=f'ticket:{self.id}',
                status='success',
                details=f'Title: {self.title}, Status: {self.get_status_display()}',
                request=getattr(self, '_request', None))

        # Если исполнитель изменился, записываем в историю
        if hasattr(self, '_executor_changed') and self._executor_changed:
            request = getattr(self, '_request', None)
            changed_by = request.user if request and hasattr(request, 'user') else None
            self.record_executor_change(
                new_executor=self.executor,
                changed_by=changed_by,
            )
            
        if is_new:
            # Отправка уведомлений только через сигналы
            self._create_initial_log_entry()
        
    def _create_initial_log_entry(self):
        """Создание начальной записи в логе"""
        from core.logging_utils import AuditLog
        AuditLog.log(
            action='ticket_create',
            target=f'ticket:{self.id}',
            status='success',
            details=f'Title: {self.title}',
            request=getattr(self, '_request', None))    
        
        # # Отправляем уведомления
        # if is_new:
        #     NotificationService.send_ticket_notification(self, 'TICKET_CREATED')
        # elif executor_changed and self.executor:
        #     NotificationService.send_ticket_notification(self, 'TICKET_ASSIGNED')
        # else:
        #     NotificationService.send_ticket_notification(self, 'TICKET_UPDATED')
    
    def delete(self, *args, **kwargs):
        try:
            ticket_id = self.id
            super().delete(*args, **kwargs)
            AuditLog.log(
                action='ticket_delete',
                target=f'ticket:{ticket_id}',
                status='success',
                details=f'Title: {self.title}',
                request=getattr(self, '_request', None))
        except Exception as e:
            AuditLog.log(
                action='ticket_delete',
                target=f'ticket:{self.id}',
                status='failed',
                details=str(e),
                request=getattr(self, '_request', None))
            raise
    
    def send_notification_sms(self):
        """Отправка SMS уведомлений всем участникам"""
        results = []
        
        # Отправка мастеру
        if self.master and self.master.phone:
            message = (
                f"Новая заявка #{self.id}\n"
                f"Адрес: {self.address}\n"
                f"Исполнитель: {self.executor.get_full_name() if self.executor else 'не назначен'}\n"
            )
            phone = self.master.phone.replace('+', '')
            results.append({
                'recipient': 'master',
                'result': Tele2SMSService.send_sms(
                    phone=phone,
                    message=message,
                    recipient_type='master',
                    ticket_id=self.id  # Добавляем недостающий аргумент
                )
            })
        
        # Отправка исполнителю
        if self.executor and self.executor.phone:
            message = (
                f"Вам назначена заявка #{self.id}\n"
                f"Адрес: {self.address}\n"
                f"Тип: {self.specialization}\n"
                # f"Ссылка: https://ваш-сайт/tickets/{self.id}/"
            )
            phone = self.executor.phone.replace('+', '')
            results.append({
            'recipient': 'executor',
            'result': Tele2SMSService.send_sms(
                phone=phone,
                message=message,
                recipient_type='worker',
                ticket_id=self.id  # Добавляем недостающий аргумент
                )
            })
        
        # Отправка жителю (если указан контактный телефон)
        if hasattr(self, 'contact_phone') and self.contact_phone:
            message = (
                f"Ваша заявка #{self.id} принята\n"
                f"Адрес: {self.address}\n"
                f"Исполнитель: {self.executor.get_full_name() if self.executor else 'будет назначен'}\n"
                f"Статус: {self.get_status_display()}"
            )
            phone = self.contact_phone.replace('+', '')
            results.append({
                'recipient': 'resident',
                'result': Tele2SMSService.send_sms(
                    phone=phone,
                    message=message,
                    recipient_type='resident',
                    ticket_id=self.id  # Добавляем недостающий аргумент
                )
            })

        return results
    
    def get_related_calls(self):
        """Получить все связанные звонки"""
        return self.call_set.all().order_by('-call_date')
    
    def get_last_call(self):
        """Получить последний связанный звонок"""
        return self.call_set.order_by('-call_date').first()

    def get_sms_statuses(self):
        """Получить статусы SMS уведомлений по этой заявке"""
        from notifications.models import SmsLog
        return SmsLog.objects.filter(ticket=self).order_by('-created_at')

    def get_push_statuses(self):
        """Получить статусы push-уведомлений по этой заявке"""
        from notifications.models import PushNotification
        return PushNotification.objects.filter(ticket=self).order_by('-created_at')

    def get_last_sms_status(self):
        """Получить последний статус SMS"""
        last_sms = self.get_sms_statuses().first()
        return last_sms.get_status_display() if last_sms else 'Нет данных'

    def get_last_push_status(self):
        """Получить последний статус push-уведомления"""
        last_push = self.get_push_statuses().first()
        return last_push.get_status_display() if last_push else 'Нет данных'
    
    def record_executor_change(self, new_executor, changed_by):
        """Запись изменения исполнителя в историю"""
        from .models import TicketExecutorHistory
        
        # Создаем запись в истории только если исполнитель действительно изменился
        if not hasattr(self, '_current_executor') or self._current_executor != new_executor:
            TicketExecutorHistory.objects.create(
                ticket=self,
                executor=new_executor,
                changed_by=changed_by
            )
            self._current_executor = new_executor
    
    
@receiver(post_save, sender=Ticket)
def send_sms_on_ticket_create(sender, instance, created, **kwargs):
    if created:
        instance.send_notification_sms()
        
@receiver(pre_save, sender=Ticket)
def ticket_pre_save(sender, instance, **kwargs):
    if not instance._state.adding:
        try:
            old_instance = Ticket.objects.get(pk=instance.pk)
            changes = []
            
            for field in instance._meta.fields:
                field_name = field.name
                old_value = getattr(old_instance, field_name)
                new_value = getattr(instance, field_name)
                
                if old_value != new_value:
                    changes.append(f"{field_name}: {old_value} -> {new_value}")
            
            if changes:
                instance._changes = ", ".join(changes)
        except Ticket.DoesNotExist:
            pass
        


@receiver(post_save, sender=Ticket)
def ticket_post_save(sender, instance, created, **kwargs):
    if not created and hasattr(instance, '_changes'):
        AuditLog.log(
            action='ticket_update_details',
            target=f'ticket:{instance.id}',
            status='success',
            details=f'Changes: {instance._changes}',
            request=getattr(instance, '_request', None))


class Specialization(models.Model):
    """Модель для хранения специализаций исполнителей"""
    class Meta:
        verbose_name = 'Специализация'
        verbose_name_plural = 'Специализации'
        ordering = ['name']

    name = models.CharField('Название', max_length=100)
    # code = models.SlugField('Код', max_length=50, unique=True, default='Нет кода')
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активна', default=True)

    def __str__(self):
        return self.name
    

class TicketExecutorHistory(models.Model):
    """Модель для хранения истории изменений исполнителей заявки"""
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='executor_history',
        verbose_name='Заявка'
    )
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executor_history_records',
        verbose_name='Исполнитель'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='changed_executor_records',
        verbose_name='Кем изменено'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата изменения'
    )
    

    class Meta:
        verbose_name = 'История исполнителя заявки'
        verbose_name_plural = 'Истории исполнителей заявок'
        ordering = ['-changed_at']

    def __str__(self):
        return f"Заявка #{self.ticket_id} - {self.executor} ({self.changed_at})"