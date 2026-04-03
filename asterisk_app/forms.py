from django import forms

from .utils import validate_phone_number
from .models import Call
from tickets.models import Ticket

class CallForm(forms.ModelForm):
    class Meta:
        model = Call
        fields = ['phone', 'call_date', 'duration', 'call_type', 'recording_path', 'user', 'ticket']
        widgets = {
            'call_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    def clean_phone(self):
        return validate_phone_number(self.cleaned_data['phone'])

class AttachCallToTicketForm(forms.Form):
    ticket = forms.ModelChoiceField(
        queryset=Ticket.objects.all(),
        label="Выберите заявку",
        required=True
    )