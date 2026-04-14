from django import forms
from .models import Invoice

from django import forms
from .models import Invoice

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['client_name',  'tax_percentage']

    def __init__(self, *args, **kwargs):
        # We pass the user from the view to the form
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Logic: If user is NOT premium, hide the tax field
        if user and not user.is_premium:
            self.fields['tax_percentage'].widget = forms.HiddenInput()
            self.fields['tax_percentage'].initial = 0