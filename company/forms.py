from django import forms
from .models import ManagementCompany

class CompanyForm(forms.ModelForm):
    class Meta:
        model = ManagementCompany
        fields = ['name', 'address', 'phone']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }