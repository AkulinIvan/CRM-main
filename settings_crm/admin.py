from django.contrib import admin
from .models import SystemSettings, SettingsChangeLog

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False  # Запрещаем создавать новые записи
    
    def has_delete_permission(self, request, obj=None):
        return False  # Запрещаем удаление
    
    list_display = ('site_name', 'maintenance_mode', 'email_notifications')
    readonly_fields = ('id',)

@admin.register(SettingsChangeLog)
class SettingsChangeLogAdmin(admin.ModelAdmin):
    list_display = ('changed_at', 'user', 'changed_field', 'ip_address')
    list_filter = ('changed_at', 'user')
    search_fields = ('changed_field', 'old_value', 'new_value')
    readonly_fields = ('changed_at', 'user', 'changed_field', 'old_value', 'new_value', 'ip_address')
    
    def has_add_permission(self, request):
        return False