import logging
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from datetime import datetime, timedelta
from .tasks import send_ticket_sms_notifications
from company.models import ManagementCompany
from core.logging_filters import UserContextFilter
from .forms import TicketForm
from .models import Specialization, Ticket
from accounts.models import Address, User
from notifications.services import NotificationService
from core.logging_utils import AuditLog


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Прикрепляем запрос к логгеру
        logger = logging.getLogger('django.request')
        for handler in logger.handlers:
            handler.addFilter(UserContextFilter())
            
        response = self.get_response(request)
        return response


@login_required
def home(request):
    user = request.user
    visible_tickets = user.get_visible_tickets()
    stats = {
        'tickets_new': visible_tickets.filter(status='new').count(),
        'tickets_assigned': visible_tickets.filter(status='in_progress').count(),
        'tickets_completed': visible_tickets.filter(status='completed').count(),
    }
    active_executors = User.objects.filter(
        role=User.Role.EXECUTOR,
        assigned_tickets__isnull=False
    ).annotate(
        active_tickets_count=Count('assigned_tickets', 
            filter=Q(assigned_tickets__status__in=['assigned', 'in_progress']))
    ).filter(
        active_tickets_count__gt=0
    ).select_related('executor_profile').order_by('-active_tickets_count')[:10]
    
    executors_data = []
    for executor in active_executors:
        executors_data.append({
            'name': executor.get_full_name() or executor.username,
            'specialization': executor.executor_profile.specialization if hasattr(executor, 'executor_profile') else 'Не указана',
            'active_tickets': executor.active_tickets_count
        })
        
    context = {
        'stats': stats,
        'recent_tickets': visible_tickets.order_by('-created_at')[:5],
        'user_role': user.get_role_display(),
        'active_executors': executors_data
    }
    
    
    
    
    # if user.role == User.Role.MASTER:
    #     stats = {k: Ticket.objects.filter(
    #         status=k.split('_')[-1],
    #         management_company=user.management_company
    #     ).count() for k in stats}
        
    # elif user.role == User.Role.EXECUTOR:
    #     stats = {k: Ticket.objects.filter(
    #         status=k.split('_')[-1],
    #         executor=user
    #     ).count() for k in stats}
    
    context.update({
        'stats': stats,
        'recent_tickets': Ticket.objects.all().order_by('-created_at')[:5],
    })
    
    return render(request, 'tickets/home.html', context)

@login_required
def ticket_list(request):
    # Получаем все параметры фильтрации из GET-запроса
    search_query = request.GET.get('search', '')
    status_filter = request.GET.getlist('status', [])
    priority_filter = request.GET.getlist('priority', [])
    date_filter = request.GET.get('date', '')
    date_range = request.GET.get('date_range', '')
    creator_filter = request.GET.get('creator', '')
    executor_filter = request.GET.get('executor', '')
    master_filter = request.GET.get('master', '')
    company_filter = request.GET.get('company', '')
    specialization_filter = request.GET.get('specialization', '')

    # Получаем заявки, видимые текущему пользователю
    tickets = request.user.get_visible_tickets()

    # Расширенный поиск
    if search_query:
        tickets = tickets.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(address__icontains=search_query) |
            Q(comments__text__icontains=search_query)
        ).distinct()

    # Фильтр по статусу (множественный выбор)
    if status_filter:
        tickets = tickets.filter(status__in=status_filter)

    # Фильтр по приоритету (множественный выбор)
    if priority_filter:
        tickets = tickets.filter(priority__in=priority_filter)

    # Фильтр по дате
    if date_filter:
        today = datetime.now().date()
        if date_filter == 'today':
            tickets = tickets.filter(created_at__date=today)
        elif date_filter == 'week':
            start_date = today - timedelta(days=7)
            tickets = tickets.filter(created_at__date__range=[start_date, today])
        elif date_filter == 'month':
            start_date = today - timedelta(days=30)
            tickets = tickets.filter(created_at__date__range=[start_date, today])

    # Фильтр по диапазону дат
    if date_range:
        start_date, end_date = date_range.split(' - ')
        start_date = datetime.strptime(start_date, '%d.%m.%Y').date()
        end_date = datetime.strptime(end_date, '%d.%m.%Y').date()
        tickets = tickets.filter(created_at__date__range=[start_date, end_date])

    # Фильтр по создателю
    if creator_filter:
        tickets = tickets.filter(created_by__id=creator_filter)

    # Фильтр по исполнителю
    if executor_filter:
        tickets = tickets.filter(executor__id=executor_filter)

    # Фильтр по мастеру
    if master_filter:
        tickets = tickets.filter(master__id=master_filter)

    # Фильтр по управляющей компании
    if company_filter and request.user.is_admin():
        tickets = tickets.filter(management_company__id=company_filter)

    # Фильтр по специализации
    if specialization_filter and specialization_filter != 'all':
        tickets = tickets.filter(specialization=specialization_filter)

    specializations = Specialization.objects.filter(is_active=True)
    
    # Сортировка
    sort_by = request.GET.get('sort_by', '-created_at')
    tickets = tickets.order_by(sort_by)

    # Пагинация
    paginator = Paginator(tickets, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Контекст для шаблона
    context = {
        'page_obj': page_obj,
        'status_choices': Ticket.Status.choices,
        'priority_choices': Ticket.Priority.choices,
        'specialization_choices': Ticket._meta.get_field('specialization').choices,
        'search_query': search_query,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'date_filter': date_filter,
        'date_range': date_range,
        'creator_filter': creator_filter,
        'executor_filter': executor_filter,
        'master_filter': master_filter,
        'company_filter': company_filter,
        'specialization_filter': specialization_filter,
        'sort_by': sort_by,
        'specializations': specializations,
    }

    # Добавляем дополнительные данные для админов
    if request.user.is_admin():
        from accounts.models import User
        from company.models import ManagementCompany
        context['creators'] = User.objects.filter(created_tickets__isnull=False).distinct()
        context['executors'] = User.objects.filter(role=User.Role.EXECUTOR)
        context['masters'] = User.objects.filter(role=User.Role.MASTER)
        context['companies'] = ManagementCompany.objects.all()

    return render(request, 'tickets/ticket_list.html', context)

@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            # Собираем полный адрес
            street = request.POST.get('street', '').strip()
            building = request.POST.get('building', '').strip()
            apartment = request.POST.get('apartment', '').strip()
            
            if not street or not building:
                messages.error(request, 'Укажите улицу и дом')
                return render(request, 'tickets/create_ticket.html', {
                    'form': form,
                    'streets': Address.objects.values_list('street', flat=True).distinct(),
                    'buildings': Address.objects.values_list('building', flat=True).distinct(),
                })
            
            address = f"{street}, {building}"
            if apartment:
                address += f", кв. {apartment}"

            try:
                # Прикрепляем запрос к объекту для логирования
                ticket = form.save(commit=False)
                ticket._request = request
                ticket.created_by = request.user
                ticket.address = address
                
                
                AuditLog.log(
                    action='ticket_create',
                    target=f'ticket:{ticket.id}',
                    status='success',
                    details=f'Title: {ticket.title}',
                    request=request
                )
            
                # Устанавливаем управляющую компанию
                if hasattr(request.user, 'management_company'):
                    ticket.management_company = request.user.management_company
                else:
                    # Если у пользователя нет компании, используем первую доступную или выдаем ошибку
                    ticket.management_company = ManagementCompany.objects.first()
                    if not ticket.management_company:
                        messages.error(request, "Нет доступных управляющих компаний")
                        return redirect('tickets:create_ticket')
                    # Назначаем исполнителя и мастера автоматически
                if form.cleaned_data.get('specialization') and form.cleaned_data['specialization'] != 'none':
                    print("\nПеред назначением исполнителя")
                    print("Управляющая компания:", ticket.management_company)
                    print("Адрес:", ticket.address)
                    print("Специализация:", form.cleaned_data['specialization'])
                    
                    form.assign_executor(
                        ticket.management_company,
                        street,
                        building,
                        form.cleaned_data['specialization']
                    )

                    if 'executor' in form.cleaned_data:
                        ticket.executor = form.cleaned_data['executor']
                    if 'master' in form.cleaned_data:
                        ticket.master = form.cleaned_data['master']
                    if 'status' in form.cleaned_data:
                        ticket.status = form.cleaned_data['status']

                ticket.save()
                form.save_m2m()
                
                # # Асинхронная отправка SMS
                # send_ticket_sms_notifications.delay(ticket.id)
                
                # NotificationService.send_ticket_notification(ticket, 'TICKET_CREATED')
                
                messages.success(request, 'Заявка успешно создана! Уведомления отправлены.')
                return redirect('tickets:list')
            except Exception as e:
                AuditLog.log(
                    action='ticket_create',
                    target='ticket:new',
                    status='failed',
                    details=str(e),
                    request=request
                )
                messages.error(request, 'Ошибка при создании заявки')
                raise
    else:
        form = TicketForm(user=request.user)
    
    return render(request, 'tickets/create_ticket.html', {
        'form': form,
        'streets': Address.objects.values_list('street', flat=True).distinct(),
        'buildings': Address.objects.values_list('building', flat=True).distinct(),
    })

    

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.has_ticket_access(ticket):
        messages.error(request, 'У вас нет доступа к этой заявке')
        return redirect('tickets:list')
    
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket})

@login_required
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.can_edit_ticket(ticket):
        AuditLog.log(
            action='ticket_unauthorized_update',
            target=f'ticket:{ticket.id}',
            status='failed',
            details=f'User {request.user.username} tried to edit ticket {ticket.id}',
            request=request
        )
        messages.error(request, 'У вас нет прав для редактирования этой заявки')
        return redirect('tickets:list')

    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES, instance=ticket, user=request.user)
        if form.is_valid():
            if 'master' in form.changed_data and form.cleaned_data['master']:
                ticket.management_company = form.cleaned_data['master'].management_company
                
            old_executor = ticket.executor
            executor_changed = 'executor' in form.changed_data
                
            try:
                ticket._request = request
                
                    
                form.save()
                
                AuditLog.log(
                    action='ticket_update',
                    target=f'ticket:{ticket.id}',
                    status='success',
                    details=f'Updated by {request.user.username}',
                    request=request
                )
            
                if old_executor != ticket.executor:
                    NotificationService.send_ticket_notification(ticket, 'TICKET_ASSIGNED')
                else:
                    NotificationService.send_ticket_notification(ticket, 'TICKET_UPDATED')
                    
            
                messages.success(request, 'Заявка успешно обновлена!')
                return redirect('tickets:detail_ticket', pk=ticket.pk)
            
            except Exception as e:
                AuditLog.log(
                    action='ticket_update',
                    target=f'ticket:{ticket.id}',
                    status='failed',
                    details=str(e),
                    request=request
                )
                messages.error(request, 'Ошибка при обновлении заявки')
                raise
    else:
        form = TicketForm(instance=ticket, user=request.user)
    
    return render(request, 'tickets/ticket_update.html',
        {'form': form, 'ticket': ticket, 'executor_history': ticket.executor_history.all().order_by('-changed_at')[:5]
    })

@login_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.can_delete_ticket(ticket):
        messages.error(request, 'У вас нет прав для удаления этой заявки')
        return redirect('tickets:list')

    if request.method == 'POST':
        ticket.delete()
        messages.success(request, 'Заявка успешно удалена!')
        return redirect('tickets:list')
    
    return render(request, 'tickets/ticket_confirm_delete.html', {'ticket': ticket})


