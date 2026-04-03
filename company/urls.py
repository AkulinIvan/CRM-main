from django.urls import path
from .views import (
    company_list,
    company_detail,
    company_create,
    company_update,
    company_delete
)

app_name = 'company'

urlpatterns = [
    path('', company_list, name='company_list'),
    path('create/', company_create, name='company_create'),
    path('<int:pk>/', company_detail, name='company_detail'),
    path('<int:pk>/update/', company_update, name='company_update'),
    path('<int:pk>/delete/', company_delete, name='company_delete'),
]