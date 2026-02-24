from django import forms
from .models import Loan
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['reader', 'book', 'issue_date', 'due_date']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ReturnForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['return_date']
        widgets = {
            'return_date': forms.DateInput(attrs={'type': 'date'}),
        }

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']