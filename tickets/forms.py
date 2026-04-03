from django import forms
from django.core.exceptions import ValidationError
from .models import Ticket
from accounts.models import Address, AddressSpecializationAssignment, User
from settings_crm.utils import get_allowed_file_extensions, validate_file_extension, validate_file_size
import logging
logger = logging.getLogger(__name__)

class TicketForm(forms.ModelForm):
    street = forms.CharField(required=False, widget=forms.HiddenInput())
    building = forms.CharField(required=False, widget=forms.HiddenInput())
    apartment = forms.CharField(required=False, widget=forms.HiddenInput())
    class Meta:
        model = Ticket
        fields = [
            'title', 
            'description', 
            'status', 
            'priority', 
            'executor',
            'master', 
            'specialization',
            'files',
            'street',
            'building',
            'apartment'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'specialization': forms.Select(attrs={'class': 'form-select'}),
            'executor': forms.Select(attrs={'class': 'form-select'}),
            'master': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Ограничиваем выбор исполнителей в зависимости от роли
        if self.user:
            if self.user.is_admin() or self.user.is_coordinator():
                # Администраторы и координаторы видят всех
                self.fields['executor'].queryset = User.objects.filter(
                    role=User.Role.EXECUTOR
                )
                self.fields['master'].queryset = User.objects.filter(
                    role=User.Role.MASTER
                )
            elif self.user.is_master():
                # Мастера видят только своих исполнителей
                self.fields['executor'].queryset = User.objects.filter(
                    management_company=self.user.management_company,
                    role=User.Role.EXECUTOR
                )
                self.fields['master'].queryset = User.objects.filter(
                    pk=self.user.pk
                )
                self.fields['master'].initial = self.user
                self.fields['master'].disabled = True
            elif self.user.is_executor():
                # Исполнители не могут выбирать
                for field in ['executor', 'master', 'priority']:
                    self.fields[field].disabled = True
    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files:
            try:
                validate_file_size(files)
                validate_file_extension(files)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
            # Проверяем расширение файла
            ext = files.name.split('.')[-1].lower()
            allowed_extensions = get_allowed_file_extensions()
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    f"Файлы с расширением .{ext} не разрешены. "
                    f"Допустимые расширения: {', '.join(allowed_extensions)}"
                )
        return files
        
                    
                
    def clean(self):
        cleaned_data = super().clean()
        try:
            specialization = cleaned_data.get('specialization')
            if not specialization:
                raise ValidationError("Укажите специализацию")

            # Проверка назначения исполнителя
            if self.user and self.user.is_master():
                self._validate_master_permissions(cleaned_data)

            return cleaned_data
        except Exception as e:
            logger.error(f"Form validation error: {str(e)}")
            raise ValidationError("Произошла ошибка при проверке данных")
    
    def _validate_master_permissions(self, cleaned_data):
        """Проверка прав мастера на назначение исполнителей"""
        if 'executor' in cleaned_data:
            executor = cleaned_data['executor']
            if executor.management_company != self.user.management_company:
                raise ValidationError("Вы можете назначать только своих исполнителей")
    
    
    def assign_executor(self, management_company, street, building, specialization):
        try:
            print(f"\nПоиск адреса: {street}, {building}, компания: {management_company}")
            address = Address.objects.filter(
                street=street,
                building=building,
                management_company=management_company
            ).first()

            if not address:
                print("Адрес не найден!")
                return
            print(f"Найден адрес: {address}")
            print(f"Поиск назначения для специализации: {specialization}")
        
            assignment = AddressSpecializationAssignment.objects.filter(
                address=address,
                specialization=specialization
            ).first()

            if not assignment:
                print("Назначение не найдено!")
                return

            print(f"Найдено назначение: {assignment}")
        
            if assignment.executor:
                print(f"Назначаем основного исполнителя: {assignment.executor}")
                self.cleaned_data['executor'] = assignment.executor
                self.cleaned_data['status'] = Ticket.Status.ASSIGNED

                if assignment.executor.management_company:
                    master = assignment.executor.management_company.user_set.filter(
                        role=User.Role.MASTER
                    ).first()
                    if master:
                        print(f"Назначаем мастера: {master}")
                        self.cleaned_data['master'] = master

            # elif assignment.backup_executor:
            #     print(f"Назначаем резервного исполнителя: {assignment.backup_executor}")
            #     self.cleaned_data['executor'] = assignment.backup_executor
            #     self.cleaned_data['status'] = Ticket.Status.ASSIGNED

            #     if assignment.backup_executor.management_company:
            #         master = assignment.backup_executor.management_company.user_set.filter(
            #             role=User.Role.MASTER
            #         ).first()
            #         if master:
            #             print(f"Назначаем мастера: {master}")
            #             self.cleaned_data['master'] = master
    
        except Exception as e:
            print(f"Ошибка назначения исполнителя: {e}")
            raise