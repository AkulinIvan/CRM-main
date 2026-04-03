from django import forms
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from .models import SystemSettings

class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = '__all__'
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'maintenance_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'default_ticket_priority': forms.Select(attrs={'class': 'form-select'}),
            'theme_color': forms.Select(attrs={'class': 'form-select'}),
            'allowed_file_types': forms.TextInput(attrs={'class': 'form-control'}),
            'email_from': forms.EmailInput(attrs={'class': 'form-control'}),
            'telegram_bot_token': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_chat_id': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    site_logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'svg'])]
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Проверка настроек файлов
        if cleaned_data.get('allow_file_attachments') and not cleaned_data.get('allowed_file_types'):
            raise ValidationError("Укажите разрешенные типы файлов при включенных вложениях")
        
        # Проверка Telegram настроек
        if cleaned_data.get('telegram_notifications'):
            if not cleaned_data.get('telegram_bot_token'):
                raise ValidationError("Укажите токен бота Telegram для включения уведомлений")
            if not cleaned_data.get('telegram_chat_id'):
                raise ValidationError("Укажите ID чата Telegram для включения уведомлений")
        
        return cleaned_data
    
    def clean_max_file_size_mb(self):
        data = self.cleaned_data['max_file_size_mb']
        if data > 50 and not self.cleaned_data['allow_file_attachments']:
            raise ValidationError("Разрешите прикрепление файлов для установки этого параметра")
        return data
    
    def clean_password_min_length(self):
        data = self.cleaned_data['password_min_length']
        if data < 6 and self.cleaned_data['require_complex_password']:
            raise ValidationError("Минимальная длина пароля должна быть не менее 6 символов при сложных паролях")
        return data