from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.system_settings, name='system_settings'),
    path('security/', views.security_settings, name='security_settings'),
    path('notifications/', views.notification_settings, name='notification_settings'),
    path('interface/', views.interface_settings, name='interface_settings'),
    path('test-telegram/', views.test_telegram_notification, name='test_telegram_notification'),
]