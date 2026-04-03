from datetime import timezone
from sqlite3 import IntegrityError
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from company.models import ManagementCompany
from core.logging_utils import AuditLog
from settings_crm.models import SystemSettings
from accounts.models import Address, AddressSpecializationAssignment, ExecutorProfile, User
from .forms import AddressAssignmentForm, ExecutorForm, ExecutorProfileForm, MasterForm, UserRegistrationForm, UserLoginForm
from django.utils.crypto import get_random_string

password = get_random_string(12)

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Проверяем, не заблокирован ли пользователь
            if user.login_blocked_until and user.login_blocked_until > timezone.now():
                remaining_time = user.login_blocked_until - timezone.now()
                messages.error(
                    request, 
                    f'Ваш аккаунт временно заблокирован. Попробуйте через {remaining_time.seconds // 60} минут'
                )
                return redirect('accounts:login')
            
            login(request, user)
            # Сбрасываем счетчик попыток при успешном входе
            user.login_attempts = 0
            user.save()
            
            messages.success(request, f'Добро пожаловать, {user.get_full_name()}!')
            return redirect('home')
        else:
            # Увеличиваем счетчик неудачных попыток
            username = form.cleaned_data.get('username')
            if username:
                try:
                    user = User.objects.get(username=username)
                    user.login_attempts += 1
                    if user.login_attempts >= settings.LOGIN_ATTEMPTS_LIMIT:
                        user.login_blocked_until = timezone.now() + timezone.timedelta(
                            minutes=settings.LOGIN_BLOCK_TIME_MINUTES
                        )
                    user.save()
                except User.DoesNotExist:
                    pass
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    AuditLog.log(
        action='user_logout',
        target=f'user:{request.user.username}',
        status='success',
        details='User logged out successfully',
        request=request
    )
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы')
    return redirect('accounts:login')



@login_required
def executor_list(request):
    # Проверка прав доступа
    if not (request.user.is_admin or request.user.is_coordinator or request.user.is_master):
        messages.error(request, 'У вас нет прав для просмотра сотрудников')
        return redirect('home')
    
    # Получаем исполнителей в зависимости от роли
    if request.user.is_admin or request.user.is_coordinator:
        executors = User.objects.filter(role=User.Role.EXECUTOR)
    elif request.user.is_master:
        executors = User.objects.filter(
            role=User.Role.EXECUTOR,
            management_company=request.user.management_company
        )
    
    return render(request, 'accounts/executor_list.html', {
        'executors': executors,
        'can_create': request.user.is_admin or request.user.is_coordinator
    })

@login_required
def executor_detail(request, pk):
    executor = get_object_or_404(User, pk=pk, role=User.Role.EXECUTOR)
    
    # Проверка прав доступа
    if not (request.user.is_admin or 
            request.user.is_coordinator or
            (request.user.is_master and executor.management_company == request.user.management_company) or
            (request.user.is_executor and executor.pk == request.user.pk)):
        messages.error(request, 'У вас нет прав для просмотра этого исполнителя')
        return redirect('accounts:executor_list')
    
    return render(request, 'accounts/executor_detail.html', {
        'executor': executor,
        'can_edit': request.user.is_admin or request.user.is_coordinator or
                (request.user.is_master and executor.management_company == request.user.management_company),
        'can_delete': request.user.is_admin or request.user.is_coordinator
    })

@login_required
def executor_create(request):
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для создания сотрудников')
        return redirect('accounts:executor_list')
    
    if request.method == 'POST':
        form = ExecutorForm(request.POST, user=request.user)
        profile_form = ExecutorProfileForm(request.POST)
        
        if form.is_valid() and profile_form.is_valid():
            try:
                executor = form.save(commit=False)
                executor.set_password(password)
                executor.role = User.Role.EXECUTOR
                executor.save()

                profile = executor.executor_profile
                profile.specialization = profile_form.cleaned_data['specialization']
                if not profile_form.cleaned_data.get('specialization'):
                    profile_form.add_error('specialization', 'Необходимо указать специализацию')
                profile.save()
                
                messages.success(request, 'Исполнитель успешно создан')
                return redirect('accounts:executor_detail', pk=executor.pk)
            except IntegrityError:
                messages.error(request, 'Ошибка при создании профиля исполнителя')
                form.add_error(None, 'Этот пользователь уже является исполнителем')
        
            return render(request, 'accounts/executor_form.html', {
                'form': form,
                'profile_form': profile_form,
                'title': 'Создание исполнителя'
            })
        else:
            messages.error(request, 'Исправьте ошибки в форме')
    else:
        form = ExecutorForm(user=request.user)
        profile_form = ExecutorProfileForm()
    
    return render(request, 'accounts/executor_form.html', {
        'form': form,
        'profile_form': profile_form,
        'title': 'Создание исполнителя'
    })
@login_required
def executor_update(request, pk):
    executor = get_object_or_404(User, pk=pk, role=User.Role.EXECUTOR)
    
    
    executor_profile, created = ExecutorProfile.objects.get_or_create(user=executor)
    
    # Проверка прав доступа
    if not (request.user.is_admin or 
            request.user.is_coordinator or
            (request.user.is_master and executor.management_company == request.user.management_company) or
            (request.user.is_executor and executor.pk == request.user.pk)):
        messages.error(request, 'У вас нет прав для редактирования этого исполнителя')
        return redirect('accounts:executor_list')
    
    if request.method == 'POST':
        form = ExecutorForm(request.POST, instance=executor, user=request.user)
        profile_form = ExecutorProfileForm(request.POST, instance=executor.executor_profile)
        
        if form.is_valid() and profile_form.is_valid():
            form.save()
            profile_form.save()
            messages.success(request, 'Исполнитель успешно обновлен')
            return redirect('accounts:executor_detail', pk=executor.pk)
    else:
        form = ExecutorForm(instance=executor, user=request.user)
        profile_form = ExecutorProfileForm(instance=executor.executor_profile)
    
    return render(request, 'accounts/executor_form.html', {
        'form': form,
        'profile_form': profile_form,
        'title': 'Редактирование исполнителя',
        'executor': executor
    })

@login_required
def executor_delete(request, pk):
    executor = get_object_or_404(User, pk=pk, role=User.Role.EXECUTOR)
    
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для удаления сотрудников')
        return redirect('accounts:executor_list')

    # Получаем доступных исполнителей для переназначения
    available_executors = User.objects.filter(
        role=User.Role.EXECUTOR,
        executor_profile__specialization=executor.executor_profile.specialization
    ).exclude(pk=executor.pk)
    
    if request.method == 'POST':
        new_executor_id = request.POST.get('new_executor')
        
            
        if executor.assigned_tickets.exists() and not new_executor_id:
            messages.error(request, 'Необходимо выбрать нового исполнителя для переназначения заявок')
            return redirect('accounts:executor_delete', pk=executor.pk)
        
        # Переназначаем заявки, если указан новый исполнитель
        if new_executor_id:
            new_executor = get_object_or_404(User, pk=new_executor_id)
            if new_executor.management_company != executor.management_company:
                messages.error(request, 'Новый исполнитель должен быть из той же компании')
                return redirect('accounts:executor_delete', pk=executor.pk)
        
        executor.delete()
        messages.success(request, 'Исполнитель успешно удален, заявки переназначены')
        return redirect('accounts:executor_list')
    
    return render(request, 'accounts/executor_confirm_delete.html', {
        'executor': executor,
        'available_executors': available_executors
    })
    

@login_required
def master_list(request):
    if not (request.user.is_admin or request.user.is_coordinator or request.user.is_dispatcher):
        messages.error(request, 'У вас нет прав для просмотра списка мастеров')
        return redirect('home')
    
    if request.user.is_admin or request.user.is_coordinator:
        masters = User.objects.filter(role=User.Role.MASTER)
    else:
        masters = User.objects.filter(
            role=User.Role.MASTER,
            management_company=request.user.management_company
        )
    
    return render(request, 'accounts/master_list.html', {
        'masters': masters,
        'can_create': request.user.is_admin or request.user.is_coordinator
    })

@login_required
def master_create(request):
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для создания мастеров')
        return redirect('accounts:master_list')
    
    if request.method == 'POST':
        form = MasterForm(request.POST, user=request.user)
        if form.is_valid():
            master = form.save(commit=False)
            master.set_password('defaultpassword')
            master.save()
            messages.success(request, 'Мастер успешно создан')
            return redirect('accounts:master_detail', pk=master.pk)
    else:
        form = MasterForm(user=request.user)
    
    return render(request, 'accounts/master_form.html', {
        'form': form,
        'title': 'Создание мастера'
    })

@login_required
def master_detail(request, pk):
    master = get_object_or_404(User, pk=pk, role=User.Role.MASTER)
    
    if not (request.user.is_admin or 
            request.user.is_coordinator or
            (hasattr(request.user, 'management_company') and 
            request.user.management_company == master.management_company)):
        messages.error(request, 'У вас нет прав для просмотра этого мастера')
        return redirect('accounts:master_list')
    
    available_executors = User.objects.filter(
        role=User.Role.EXECUTOR,
        management_company=master.management_company
    ).exclude(pk__in=master.get_subordinates().values_list('pk', flat=True))
    
    return render(request, 'accounts/master_detail.html', {
        'master': master,
        'executors': master.get_subordinates(),
        'available_executors': available_executors,
        'can_edit': request.user.is_admin or request.user.is_coordinator,
        'can_delete': request.user.is_admin or request.user.is_coordinator
    })

@login_required
def master_update(request, pk):
    master = get_object_or_404(User, pk=pk, role=User.Role.MASTER)
    
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для редактирования мастеров')
        return redirect('accounts:master_list')
    
    if request.method == 'POST':
        form = MasterForm(request.POST, instance=master, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Мастер успешно обновлен')
            return redirect('accounts:master_detail', pk=master.pk)
    else:
        form = MasterForm(instance=master, user=request.user)
    
    return render(request, 'accounts/master_form.html', {
        'form': form,
        'title': 'Редактирование мастера',
        'master': master
    })

@login_required
def master_delete(request, pk):
    master = get_object_or_404(User, pk=pk, role=User.Role.MASTER)
    
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для удаления мастеров')
        return redirect('accounts:master_list')
    
    if request.method == 'POST':
        # Переназначаем исполнителей другому мастеру
        new_master_id = request.POST.get('new_master')
        if master.get_subordinates().exists() and not new_master_id:
            messages.error(request, 'Необходимо выбрать нового мастера для переназначения исполнителей')
            return redirect('accounts:master_delete', pk=master.pk)
        
        if new_master_id:
            new_master = get_object_or_404(User, pk=new_master_id)
            master.get_subordinates().update(management_company=new_master.management_company)
        
        master.delete()
        messages.success(request, 'Мастер успешно удален')
        return redirect('accounts:master_list')
    
    available_masters = User.objects.filter(
        role=User.Role.MASTER
    ).exclude(pk=master.pk)
    
    return render(request, 'accounts/master_confirm_delete.html', {
        'master': master,
        'available_masters': available_masters
    })
    

@login_required
def add_executor_to_master(request, master_pk):
    master = get_object_or_404(User, pk=master_pk, role=User.Role.MASTER)
    
    if not (request.user.is_admin or request.user.is_coordinator or request.user == master):
        messages.error(request, 'У вас нет прав для добавления исполнителей')
        return redirect('accounts:master_detail', pk=master.pk)
    
    if request.method == 'POST':
        executor_id = request.POST.get('executor_id')
        try:
            executor = User.objects.get(
                pk=executor_id,
                role=User.Role.EXECUTOR,
                management_company=master.management_company
            )
            # Обновляем исполнителя (если нужно)
            # executor.some_field = some_value
            executor.save()
            messages.success(request, f'Исполнитель {executor.get_full_name} добавлен к мастеру')
        except User.DoesNotExist:
            messages.error(request, 'Исполнитель не найден или не принадлежит этой компании')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect('accounts:master_detail', pk=master.pk)
    
    return redirect('accounts:master_detail', pk=master.pk)

@login_required
def remove_executor_from_master(request, master_pk, executor_pk):
    master = get_object_or_404(User, pk=master_pk, role=User.Role.MASTER)
    executor = get_object_or_404(User, pk=executor_pk, role=User.Role.EXECUTOR)
    
    if not (request.user.is_admin or request.user.is_coordinator or request.user == master):
        messages.error(request, 'У вас нет прав для удаления исполнителя')
        return redirect('accounts:master_detail', pk=master.pk)
    
    if executor.management_company == master.management_company:
        # Можно реализовать логику переназначения или просто оставить без мастера
        executor.management_company = None
        executor.save()
        messages.success(request, f'Исполнитель {executor.get_full_name} удален из подчинения')
    
    return redirect('accounts:master_detail', pk=master.pk)


@login_required
def assignment_list(request):
    assignments = AddressSpecializationAssignment.objects.select_related('address', 'executor', 'specialization')
    return render(request, 'accounts/assignment_list.html', {'assignments': assignments})

@login_required
def create_assignment(request):
    if request.method == 'POST':
        form = AddressAssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounts:assignment_list')
    else:
        form = AddressAssignmentForm()
    return render(request, 'accounts/assignment_form.html', {'form': form})

@login_required
def update_assignment(request, pk):
    assignment = get_object_or_404(AddressSpecializationAssignment, pk=pk)
    if request.method == 'POST':
        form = AddressAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            return redirect('accounts:assignment_list')
    else:
        form = AddressAssignmentForm(instance=assignment)
    return render(request, 'accounts/assignment_form.html', {'form': form})

@login_required
def address_list(request):
    management_companies = ManagementCompany.objects.all()
    active_company_id = request.GET.get('company')
    
    addresses = Address.objects.select_related('management_company').prefetch_related('assignments__specialization', 'assignments__executor')
    
    if active_company_id:
        active_company = get_object_or_404(ManagementCompany, pk=active_company_id)
        addresses = addresses.filter(management_company=active_company)
    else:
        active_company = None
    
    return render(request, 'accounts/address_list.html', {
        'addresses': addresses,
        'management_companies': management_companies,
        'active_company': active_company
    })