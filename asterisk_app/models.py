# asterisk_app/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()

class Call(models.Model):
    CALL_TYPES = (
        ('incoming', 'Входящий'),
        ('outgoing', 'Исходящий'),
        ('missed', 'Пропущенный'),
        ('voicemail', 'Голосовая почта'),
    )
    
    CALL_STATUS = (
        ('started', 'Начат'),
        ('answered', 'Отвечен'),
        ('completed', 'Завершен'),
        ('failed', 'Неудачный'),
    )
    
    phone = models.CharField(max_length=20, verbose_name='Номер телефона', db_index=True)
    unique_id = models.CharField(max_length=64, unique=True, verbose_name='Уникальный ID звонка')
    call_date = models.DateTimeField(default=timezone.now, verbose_name='Дата и время звонка')
    duration = models.IntegerField(default=0, verbose_name='Длительность (сек)')
    call_type = models.CharField(max_length=20, choices=CALL_TYPES, verbose_name='Тип звонка')
    call_status = models.CharField(max_length=20, choices=CALL_STATUS, default='started', verbose_name='Статус')
    recording_path = models.CharField(max_length=512, blank=True, verbose_name='Путь к записи')
    recording_url = models.URLField(blank=True, verbose_name='URL записи')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания записи')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Сотрудник')
    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Связанная заявка')
    source = models.CharField(max_length=50, default='asterisk', verbose_name='Источник')
    is_processed = models.BooleanField(default=False, verbose_name='Обработан')
    
    # Дополнительные поля
    caller_id_name = models.CharField(max_length=100, blank=True, verbose_name='Имя звонящего')
    destination = models.CharField(max_length=50, blank=True, verbose_name='Назначение')
    context = models.CharField(max_length=50, blank=True, verbose_name='Контекст')
    extension = models.CharField(max_length=20, blank=True, verbose_name='Extension')
    channel = models.CharField(max_length=100, blank=True, verbose_name='Канал')
    dst_channel = models.CharField(max_length=100, blank=True, verbose_name='Канал назначения')
    account_code = models.CharField(max_length=50, blank=True, verbose_name='Код учетной записи')
    userfield = models.CharField(max_length=255, blank=True, verbose_name='Пользовательское поле')
    
    class Meta:
        verbose_name = 'Звонок'
        verbose_name_plural = 'Звонки'
        ordering = ['-call_date']
        indexes = [
            models.Index(fields=['call_date', 'call_type']),
            models.Index(fields=['phone', 'call_date']),
            models.Index(fields=['unique_id']),
            models.Index(fields=['call_status']),
        ]
    
    def __str__(self):
        return f"{self.get_call_type_display()} от {self.phone} ({self.call_date})"
    
    def get_recording_url(self):
        if self.recording_url:
            return self.recording_url
        if self.recording_path:
            return f"/media/{self.recording_path}"
        return None


class CallEvent(models.Model):
    EVENT_TYPES = (
        ('Newchannel', 'Новый канал'),
        ('Newstate', 'Новое состояние'),
        ('Newcallerid', 'Новый CallerID'),
        ('Dial', 'Набор номера'),
        ('DialBegin', 'Начало набора'),
        ('DialEnd', 'Конец набора'),
        ('Hangup', 'Отбой'),
        ('HangupRequest', 'Запрос отбоя'),
        ('Ringing', 'Звонок'),
        ('Answer', 'Ответ'),
        ('VarSet', 'Установка переменной'),
    )
    
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, verbose_name='Тип события')
    event_time = models.DateTimeField(default=timezone.now, verbose_name='Время события')
    data = models.JSONField(default=dict, verbose_name='Данные события')
    
    class Meta:
        verbose_name = 'Событие звонка'
        verbose_name_plural = 'События звонков'
        ordering = ['event_time']
    
    def __str__(self):
        return f"{self.event_type} - {self.call.phone} at {self.event_time}"


class CallHistory(models.Model):
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='history')
    changed_at = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField()
    
    class Meta:
        verbose_name = 'История звонка'
        verbose_name_plural = 'История звонков'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"History #{self.id} for call {self.call.id} at {self.changed_at}"