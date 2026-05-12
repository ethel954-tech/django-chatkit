from django import forms
from .models import CallSession


class InitiateCallForm(forms.Form):
    """Form for initiating a call"""
    CALL_TYPE_CHOICES = [
        ('audio', '📞 Audio Call'),
        ('video', '📹 Video Call'),
    ]
    
    call_type = forms.ChoiceField(
        choices=CALL_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio'
        })
    )
