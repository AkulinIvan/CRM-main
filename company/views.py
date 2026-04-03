from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from accounts.models import User


from .forms import CompanyForm
from .models import ManagementCompany

login_required
def company_list(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    # Проверка прав доступа
    if not (request.user.role in [User.Role.ADMIN, User.Role.COORDINATOR, User.Role.DISPATCHER]):
        messages.error(request, 'У вас нет прав для просмотра списка компаний')
        return redirect('home')
    
    companies = ManagementCompany.objects.all()
    return render(request, 'company/company_list.html', {
        'companies': companies,
        'can_create': request.user.is_admin or request.user.is_coordinator
    })

@login_required
def company_detail(request, pk):
    from accounts.models import User
    company = get_object_or_404(ManagementCompany, pk=pk)
    
    user_has_access = False
    
    # Проверяем доступ пользователя к информации о компании
    if request.user.role in [User.Role.ADMIN, User.Role.COORDINATOR, User.Role.DISPATCHER]:
        user_has_access = True
    # Мастера и исполнители имеют доступ только к своей компании
    elif request.user.management_company == company:
        user_has_access = True
    
    if not user_has_access:
        messages.error(request, 'У вас нет прав для просмотра этой компании')
        return redirect('company:company_list')
    
    context = {
        'company': company,
        'can_edit': request.user.role in [User.Role.ADMIN, User.Role.COORDINATOR],
        'can_delete': request.user.role == [User.Role.ADMIN, User.Role.COORDINATOR] 
    }
    
    # Если пользователь имеет отношение к компании (не админ/координатор)
    if (hasattr(request.user, 'management_company') and 
        request.user.management_company == company):
        
        # Для мастера показываем только своих исполнителей
        if request.user.is_master():
            executors = User.objects.filter(
                management_company=company,
                role=User.Role.EXECUTOR
            )
            context.update({
                'masters': None,  # Мастер не видит других мастеров
                'executors': executors
            })
        # Для исполнителя не показываем никого
        elif request.user.is_executor():
            context.update({
                'masters': None,
                'executors': None
            })
        # Для диспетчера показываем всех
        elif request.user.is_dispatcher():
            context.update({
                'masters': company.get_masters(),
                'executors': company.get_executors()
            })
    
    # Для админа и координатора показываем всех
    elif request.user.is_admin or request.user.is_coordinator:
        context.update({
            'masters': company.get_masters(),
            'executors': company.get_executors()
        })
    
    return render(request, 'company/company_detail.html', context)

@login_required
def company_create(request):
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для создания компаний')
        return redirect('company:company_list')
    
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            messages.success(request, 'Компания успешно создана')
            return redirect('company:company_detail', pk=company.pk)
    else:
        form = CompanyForm()
    
    return render(request, 'company/company_form.html', {
        'form': form,
        'title': 'Создание компании'
    })

@login_required
def company_update(request, pk):
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для редактирования компаний')
        return redirect('company:company_list')
    
    company = get_object_or_404(ManagementCompany, pk=pk)
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Компания успешно обновлена')
            return redirect('company:company_detail', pk=company.pk)
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'company/company_form.html', {
        'form': form,
        'title': 'Редактирование компании',
        'company': company
    })

@login_required
def company_delete(request, pk):
    if not (request.user.is_admin or request.user.is_coordinator):
        messages.error(request, 'У вас нет прав для удаления компаний')
        return redirect('company:company_list')
    
    company = get_object_or_404(ManagementCompany, pk=pk)
    
    if request.method == 'POST':
        company.delete()
        messages.success(request, 'Компания успешно удалена')
        return redirect('company:company_list')
    
    return render(request, 'company/company_confirm_delete.html', {
        'company': company
    })