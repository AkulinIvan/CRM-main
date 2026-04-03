from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _

from company.models import ManagementCompany
from tickets.models import Specialization, Ticket



class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Администратор')
        COORDINATOR = 'coordinator', _('Координатор')
        DISPATCHER = 'dispatcher', _('Диспетчер')
        MASTER = 'master', _('Мастер участка')
        EXECUTOR = 'executor', _('Исполнитель')
    
    role = models.CharField(
        _('Роль'),
        max_length=20,
        choices=Role.choices,
        default=Role.DISPATCHER,
        help_text=_('Роль пользователя в системе')
    )
    phone = models.CharField(max_length=20, blank=True)
    management_company = models.ForeignKey(
        'company.ManagementCompany',  
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_('The groups this user belongs to.'),
        related_name="custom_user_set",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_set",
    )
    login_attempts = models.PositiveIntegerField(
        'Количество попыток входа',
        default=0,
        help_text='Количество неудачных попыток входа'
    )
    login_blocked_until = models.DateTimeField(
        'Заблокирован до',
        null=True,
        blank=True,
        help_text='Время, до которого пользователь заблокирован после превышения лимита попыток входа'
    )
    def __str__(self):
        return self.username
    
    

    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    def is_coordinator(self):
        return self.role == self.Role.COORDINATOR
    
    def is_dispatcher(self):
        return self.role == self.Role.DISPATCHER
    
    def is_master(self):
        return self.role == self.Role.MASTER
    
    def is_executor(self):
        return self.role == self.Role.EXECUTOR
    
    def get_visible_tickets(self):
        queryset = Ticket.objects.all()

        if self.is_admin() or self.is_coordinator():
            return queryset
        elif self.is_dispatcher():
            return queryset.filter(created_by=self)
        elif self.is_master():
            return queryset.filter(management_company=self.management_company)
        elif self.is_executor():
            # Добавляем проверку на наличие профиля
            if hasattr(self, 'executor_profile'):
                return queryset.filter(
                    executor=self,
                    management_company=self.management_company,
                    specialization=self.executor_profile.specialization
                )
            return queryset.none()

        return queryset.none()

    def get_visible_executors(self):
        """Возвращает список исполнителей, видимых текущему пользователю"""
        from .models import User
        if self.is_admin() or self.is_coordinator():
            return User.objects.filter(role=User.Role.EXECUTOR)
        elif self.is_master():
            return User.objects.filter(
                management_company=self.management_company,
                role=User.Role.EXECUTOR
            )
        return User.objects.none()
    
    def get_visible_masters(self):
        """Возвращает список мастеров, видимых текущему пользователю"""
        from .models import User
        if self.is_admin() or self.is_coordinator():
            return User.objects.filter(role=User.Role.MASTER)
        elif self.is_master():
            return User.objects.filter(pk=self.pk)
        return User.objects.none()

    def has_ticket_access(self, ticket):
        """Проверка доступа пользователя к конкретной заявке"""
        if self.role in [self.Role.ADMIN, self.Role.COORDINATOR, self.Role.DISPATCHER]:
            return True
        elif self.role == self.Role.MASTER:
            return ticket.management_company == self.management_company
        elif self.role == self.Role.EXECUTOR:
            return ticket.executor == self and ticket.management_company == self.management_company
        return False

    def can_edit_ticket(self, ticket):
        """Проверка прав на редактирование заявки"""
        if self.is_admin() or self.is_coordinator():
            return True
        elif self.is_dispatcher():
            return ticket.created_by == self
        elif self.is_master():
            return ticket.master == self or ticket.management_company == self.management_company
        elif self.is_executor():
            return (
                ticket.executor == self and
                ticket.management_company == self.management_company and
                ticket.specialization == self.executor_profile.specialization
            )
        return False

    def can_delete_ticket(self, ticket):
        """Проверка прав на удаление заявки"""
        return self.is_admin() or self.is_coordinator() or (
            self.is_dispatcher() and ticket.created_by == self
        )
        
    def get_assigned_tickets_count(self):
        return self.assigned_tickets.count()
    
    def get_in_progress_tickets_count(self):
        return self.assigned_tickets.filter(status=Ticket.Status.IN_PROGRESS).count()
    
    def get_completed_tickets_count(self):
        return self.assigned_tickets.filter(status=Ticket.Status.COMPLETED).count()
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.role == self.Role.EXECUTOR:
            self._create_executor_profile()
    
    def _create_executor_profile(self):
        if not hasattr(self, 'executor_profile'):
            ExecutorProfile.objects.get_or_create(
            user=self,
            defaults={'specialization': Specialization.objects.get_or_create(name='Other')[0]}
        )
    
        
    def get_subordinates(self):
        """
        Возвращает подчиненных (исполнителей) для мастера
        """
        if self.is_master():
            return User.objects.filter(
                management_company=self.management_company,
                role=self.Role.EXECUTOR
            )
        return User.objects.none()
    
    def get_master_executors(self):
        """
        Возвращает исполнителей, привязанных к текущему мастеру
        """
        if self.is_master():
            return self.get_subordinates()
        return User.objects.none()
    
    
class ExecutorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='executor_profile'
    )
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.PROTECT,
        related_name='executors',
        verbose_name='Специализация',
        null=True
    )
    
    def get_specialization_name(self):
        return self.specialization.name if self.specialization else 'Не указана'
    
    def __str__(self):
        return f"{self.user.username} ({self.specialization.name})"


class Address(models.Model):
    management_company = models.ForeignKey(
        ManagementCompany,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    street = models.CharField('Улица', max_length=255)
    building = models.CharField('Дом', max_length=10)
    apartment = models.CharField('Квартира', max_length=10, blank=True)
    
    class Meta:
        verbose_name = 'Адрес'
        verbose_name_plural = 'Адреса'
        unique_together = ('street', 'building', 'apartment', 'management_company')

    def __str__(self):
        return f"{self.street}, {self.building}" + (f", кв. {self.apartment}" if self.apartment else "")
    

    
class AddressSpecializationAssignment(models.Model):
    """Назначение исполнителей по специализациям на адресах"""
    address = models.ForeignKey(
        Address,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.CASCADE,
        related_name='address_assignments'
    )
    executor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='address_assignments',
        limit_choices_to={'role': User.Role.EXECUTOR}
    )
    backup_executor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backup_assignments',
        limit_choices_to={'role': User.Role.EXECUTOR}
    )
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Назначение специализации'
        verbose_name_plural = 'Назначения специализаций'
        unique_together = ('address', 'specialization')

    def __str__(self):
        return f"{self.address} - {self.specialization}"