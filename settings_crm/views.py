from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import SystemSettingsForm
from .models import SystemSettings, SettingsChangeLog
from accounts.models import User
import json

@login_required
@user_passes_test(lambda u: u.is_admin)
def system_settings(request):
    system_settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, request.FILES, instance=system_settings)
        if form.is_valid():
            # Сохраняем старые значения для лога
            old_values = {}
            for field in form.changed_data:
                old_values[field] = str(getattr(system_settings, field))
            
            # Обработка логотипа
            if 'site_logo' in request.FILES:
                logo = request.FILES['site_logo']
                fs = FileSystemStorage(location=settings.MEDIA_ROOT / 'settings')
                filename = fs.save(logo.name, logo)
                form.instance.site_logo = 'settings/' + filename
            
            form.save()
            
            # Логируем изменения
            for field in form.changed_data:
                SettingsChangeLog.objects.create(
                    user=request.user,
                    changed_field=field,
                    old_value=old_values.get(field, ''),
                    new_value=str(getattr(form.instance, field)),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            messages.success(request, 'Настройки успешно сохранены!')
            return redirect('settings:system_settings')
    else:
        form = SystemSettingsForm(instance=system_settings)
    
    change_log = SettingsChangeLog.objects.all().order_by('-changed_at')[:10]
    users = User.objects.filter(is_active=True)
    
    return render(request, 'settings_crm/system_settings.html', {
        'form': form,
        'active_tab': 'general',
        'change_log': change_log,
        'users': users
    })

@login_required
@user_passes_test(lambda u: u.is_admin)
def security_settings(request):
    system_settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=system_settings)
        if form.is_valid():
            old_values = {}
            for field in form.changed_data:
                old_values[field] = str(getattr(system_settings, field))
            
            form.save()
            
            for field in form.changed_data:
                SettingsChangeLog.objects.create(
                    user=request.user,
                    changed_field=field,
                    old_value=old_values.get(field, ''),
                    new_value=str(getattr(form.instance, field)),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            messages.success(request, 'Настройки безопасности успешно сохранены!')
            return redirect('settings:security_settings')
    else:
        form = SystemSettingsForm(instance=system_settings)
    
    return render(request, 'settings_crm/system_settings.html', {
        'form': form,
        'active_tab': 'security'
    })

@login_required
@user_passes_test(lambda u: u.is_admin)
def notification_settings(request):
    system_settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=system_settings)
        if form.is_valid():
            old_values = {}
            for field in form.changed_data:
                old_values[field] = str(getattr(system_settings, field))
            
            form.save()
            
            for field in form.changed_data:
                SettingsChangeLog.objects.create(
                    user=request.user,
                    changed_field=field,
                    old_value=old_values.get(field, ''),
                    new_value=str(getattr(form.instance, field)),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            messages.success(request, 'Настройки уведомлений успешно сохранены!')
            return redirect('settings:notification_settings')
    else:
        form = SystemSettingsForm(instance=system_settings)
    
    return render(request, 'settings_crm/system_settings.html', {
        'form': form,
        'active_tab': 'notifications'
    })

@login_required
@user_passes_test(lambda u: u.is_admin)
def interface_settings(request):
    system_settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=system_settings)
        if form.is_valid():
            old_values = {}
            for field in form.changed_data:
                old_values[field] = str(getattr(system_settings, field))
            
            form.save()
            
            for field in form.changed_data:
                SettingsChangeLog.objects.create(
                    user=request.user,
                    changed_field=field,
                    old_value=old_values.get(field, ''),
                    new_value=str(getattr(form.instance, field)),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            messages.success(request, 'Настройки интерфейса успешно сохранены!')
            return redirect('settings:interface_settings')
    else:
        form = SystemSettingsForm(instance=system_settings)
    
    return render(request, 'settings_crm/system_settings.html', {
        'form': form,
        'active_tab': 'interface'
    })

@require_POST
@staff_member_required
def test_telegram_notification(request):
    try:
        system_settings = SystemSettings.get_settings()
        if not system_settings.telegram_notifications:
            return JsonResponse({'status': 'error', 'message': 'Telegram уведомления отключены'})
        
        import requests
        message = "✅ Тестовое уведомление от системы\n\nЭто сообщение подтверждает, что настройки Telegram корректны."
        url = f"https://api.telegram.org/bot{system_settings.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': system_settings.telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return JsonResponse({'status': 'success', 'message': 'Тестовое уведомление отправлено!'})
        else:
            return JsonResponse({'status': 'error', 'message': f'Ошибка: {response.json().get("description", "Неизвестная ошибка")}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ошибка: {str(e)}'})