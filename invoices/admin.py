from django.contrib import admin

# Register your models here.
# invoices/admin.py
from django.contrib import admin
from .models import Invoice

admin.site.register(Invoice)