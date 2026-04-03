from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from tickets.models import Specialization
from settings_crm.utils import validate_password_complexity
from company.models import ManagementCompany


from .models import AddressSpecializationAssignment, ExecutorProfile, User

class UserRegistrationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('dispatcher', 'Диспетчер'),
        ('master', 'Мастер участка'),
        ('executor', 'Исполнитель'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label='Роль в системе',
        widget=forms.RadioSelect
    )
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True)
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'phone',
            'first_name',
            'last_name',
            'role',
            'password1',
            'password2'
        ]
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
            # if user.role == User.Role.EXECUTOR:
            #     ExecutorProfile.objects.create(user=user)
        return user

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_password_complexity(password)
        return password
    
class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Имя пользователя или Email',
        widget=forms.TextInput(attrs={'autofocus': True}))
    
    error_messages = {
        'invalid_login': 'Неверное имя пользователя или пароль',
        'inactive': 'Этот аккаунт неактивен',
    }
    


class ExecutorForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'management_company']
        widgets = {
            'management_company': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and not user.is_admin():
            self.fields['management_company'].queryset = ManagementCompany.objects.filter(
                pk=user.management_company.pk
            )
            self.fields['management_company'].initial = user.management_company
            self.fields['management_company'].widget.attrs.update({
                'disabled': True,
                'readonly': True,
                'class': 'form-select disabled'
            })
            self.fields['management_company'].disabled = True
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.EXECUTOR
        
        if commit:
            user.save()
            
        
        return user
    
    
class ExecutorProfileForm(forms.ModelForm):
    specialization = forms.ModelChoiceField(
        queryset=Specialization.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        label='Специализация'
    )
    
    class Meta:
        model = ExecutorProfile
        fields = ['specialization']
        
        
        

class MasterForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'management_company']
        widgets = {
            'management_company': forms.Select(attrs={'class': 'form-select'})
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['management_company'].queryset = ManagementCompany.objects.all()
        if user and not user.is_admin:
            self.fields['management_company'].initial = user.management_company
            self.fields['management_company'].disabled = True
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.MASTER
        if commit:
            user.save()
        return user
    
class AddressAssignmentForm(forms.ModelForm):
    class Meta:
        model = AddressSpecializationAssignment
        fields = ['address', 'executor', 'backup_executor', 'specialization', 'notes']
        widgets = {
            'address': forms.Select(attrs={'class': 'form-select'}),
            'executor': forms.Select(attrs={'class': 'form-select'}),
            'backup_executor': forms.Select(attrs={'class': 'form-select'}),
            'specialization': forms.Select(attrs={'class': 'form-select'}),
        }