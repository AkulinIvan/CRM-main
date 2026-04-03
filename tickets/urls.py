from django.urls import path
from tickets import views
from tickets.api import get_buildings, get_executors_for_master

app_name = 'tickets'

urlpatterns = [
    path('', views.ticket_list, name='list'),
    path('create/', views.ticket_create, name='create_ticket'),
    path('<int:pk>/', views.ticket_detail, name='detail_ticket'),
    path('<int:pk>/update/', views.ticket_update, name='update_ticket'),
    path('<int:pk>/delete/', views.ticket_delete, name='delete_ticket'),
    path('api/buildings/', get_buildings, name='get_buildings'),
    path('api/executors/', get_executors_for_master, name='get_executors_for_master'),
]
