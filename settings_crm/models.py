from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class SystemSettings(models.Model):
    class Meta:
        verbose_name = 'Настройка системы'
        verbose_name_plural = 'Настройки системы'

    # Основные настройки
    site_name = models.CharField('Название системы', max_length=100, default='CRM Заявки')
    site_logo = models.ImageField('Логотип системы', upload_to='settings/', null=True, blank=True)
    maintenance_mode = models.BooleanField('Режим технического обслуживания', default=False)
    maintenance_message = models.TextField('Сообщение при обслуживании', blank=True, default='Система временно недоступна. Пожалуйста, попробуйте позже.')
    
    # Настройки заявок
    default_ticket_priority = models.CharField(
        'Приоритет по умолчанию',
        max_length=20,
        choices=[
            ('low', 'Низкий'),
            ('medium', 'Средний'),
            ('high', 'Высокий'),
            ('critical', 'Критический')
        ],
        default='medium'
    )
    ticket_expiration_days = models.PositiveIntegerField(
        'Дней до автоматического закрытия неактивных заявок',
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    allow_file_attachments = models.BooleanField('Разрешить прикрепление файлов', default=True)
    max_file_size_mb = models.PositiveIntegerField(
        'Максимальный размер файла (МБ)',
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    allowed_file_types = models.CharField(
        'Разрешенные типы файлов (через запятую)',
        max_length=255,
        default='jpg,jpeg,png,gif,pdf,doc,docx,xls,xlsx'
    )
    
    # Настройки безопасности
    login_attempts_limit = models.PositiveIntegerField(
        'Лимит попыток входа',
        default=5,
        validators=[MinValueValidator(3), MaxValueValidator(10)]
    )
    login_block_time_minutes = models.PositiveIntegerField(
        'Время блокировки при превышении попыток (минут)',
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(1440)]
    )
    password_expiration_days = models.PositiveIntegerField(
        'Срок действия пароля (дней)',
        default=90,
        validators=[MinValueValidator(30), MaxValueValidator(365)]
    )
    require_complex_password = models.BooleanField('Требовать сложный пароль', default=True)
    password_min_length = models.PositiveIntegerField(
        'Минимальная длина пароля',
        default=8,
        validators=[MinValueValidator(6), MaxValueValidator(30)]
    )
    
    # Настройки уведомлений
    email_notifications = models.BooleanField('Email уведомления', default=True)
    email_from = models.EmailField('Email для отправки', default='noreply@example.com')
    telegram_notifications = models.BooleanField('Telegram уведомления', default=False)
    telegram_bot_token = models.CharField('Токен бота Telegram', max_length=100, blank=True)
    telegram_chat_id = models.CharField('ID чата Telegram', max_length=50, blank=True)
    
    notify_on_ticket_create = models.BooleanField('Уведомлять о создании заявки', default=True)
    notify_on_ticket_update = models.BooleanField('Уведомлять об изменении заявки', default=True)
    notify_on_ticket_complete = models.BooleanField('Уведомлять о завершении заявки', default=True)
    notify_on_ticket_assign = models.BooleanField('Уведомлять о назначении заявки', default=True)
    
    # Настройки интерфейса
    theme_color = models.CharField(
        'Цветовая тема',
        max_length=20,
        choices=[
            ('blue', 'Синяя'),
            ('green', 'Зеленая'),
            ('orange', 'Оранжевая'),
            ('dark', 'Темная')
        ],
        default='blue'
    )
    font_size = models.PositiveIntegerField(
        'Размер шрифта (px)',
        default=16,
        validators=[MinValueValidator(12), MaxValueValidator(24)]
    )
    compact_mode = models.BooleanField('Компактный режим', default=False)
    show_avatars = models.BooleanField('Показывать аватары', default=True)
    
    # Методы
    def __str__(self):
        return 'Настройки системы'
    
    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1  # Гарантируем, что будет только одна запись
        super().save(*args, **kwargs)


class SettingsChangeLog(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_field = models.CharField(max_length=100)
    old_value = models.TextField()
    new_value = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Лог изменений настроек'
        verbose_name_plural = 'Логи изменений настроек'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"Изменение {self.changed_field} в {self.changed_at}"