from django.contrib import admin

from tickets.models import Ticket, Specialization, TicketExecutorHistory

# admin.site.register(Ticket)
admin.site.register(Specialization)
admin.site.register(TicketExecutorHistory)

from notifications.models import SmsLog, PushNotification

class SmsLogInline(admin.TabularInline):
    model = SmsLog
    extra = 0
    readonly_fields = ('created_at', 'updated_at', 'status')
    can_delete = False

class PushNotificationInline(admin.TabularInline):
    model = PushNotification
    extra = 0
    readonly_fields = ('created_at', 'status')
    can_delete = False

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'priority', 'executor', 
                   'sms_status', 'push_status', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'description', 'address')
    inlines = [SmsLogInline, PushNotificationInline]
    
    def sms_status(self, obj):
        last_sms = obj.get_sms_statuses().first()
        return last_sms.get_status_display() if last_sms else '-'
    sms_status.short_description = 'SMS статус'
    
    def push_status(self, obj):
        last_push = obj.get_push_statuses().first()
        return last_push.get_status_display() if last_push else '-'
    push_status.short_description = 'Push статус'