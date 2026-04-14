from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.urls import path
from . import views
from django.shortcuts import render

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_invoice, name='create_invoice'),
    path('upgrade/', lambda request: render(request, 'invoices/upgrade.html'), name='upgrade'),
    path('invoice/<int:invoice_id>/download/', views.download_invoice, name='download_invoice'),
]