from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email", 'logo',)

from django import forms
from .models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        # These are the only fields the user can edit
        fields = ['first_name', 'last_name', 'logo']