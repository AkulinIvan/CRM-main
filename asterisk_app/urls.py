
from django.urls import path
from .views import asterisk_webhook
from . import views

app_name = 'asterisk_app'

urlpatterns = [
    path('', views.call_list, name='call_list'),
    path('<int:pk>/', views.call_detail, name='call_detail'),
    path('<int:call_id>/attach/', views.attach_call_to_ticket, name='attach_to_ticket'),
    path('ticket/<int:ticket_id>/', views.ticket_calls, name='ticket_calls'),
    path('api/calls/webhook/', asterisk_webhook, name='call_webhook'),
]