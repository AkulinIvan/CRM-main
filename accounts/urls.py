from django.urls import path
from accounts.views import (
    address_list,
    assignment_list,
    create_assignment,
    register_view, 
    login_view, 
    logout_view,
    executor_list,
    executor_detail,
    executor_create,
    executor_update,
    executor_delete,
    master_list,
    master_detail,
    master_create,
    master_update,
    master_delete,
    add_executor_to_master,
    remove_executor_from_master,
    update_assignment
)
app_name = 'accounts'

urlpatterns = [
    # Аутентификация
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    # Исполнители
    path('executors/', executor_list, name='executor_list'),
    path('executors/create/', executor_create, name='executor_create'),
    path('executors/<int:pk>/', executor_detail, name='executor_detail'),
    path('executors/<int:pk>/update/', executor_update, name='executor_update'),
    path('executors/<int:pk>/delete/', executor_delete, name='executor_delete'),
    # Мастера компании
    path('masters/', master_list, name='master_list'),
    path('masters/create/', master_create, name='master_create'),
    path('masters/<int:pk>/', master_detail, name='master_detail'),
    path('masters/<int:pk>/update/', master_update, name='master_update'),
    path('masters/<int:pk>/delete/', master_delete, name='master_delete'),
    path('masters/<int:master_pk>/add_executor/', add_executor_to_master, name='add_executor_to_master'),
    path('masters/<int:master_pk>/remove_executor/<int:executor_pk>/', remove_executor_from_master, name='remove_executor_from_master'),
    # назначение исполнителей на адреса
    path('assignments/', assignment_list, name='assignment_list'),
    path('assignments/create/', create_assignment, name='create_assignment'),
    path('assignments/<int:pk>/update/', update_assignment, name='update_assignment'),
    # адреса
    path('addresses/', address_list, name='address_list')
]
