from django.urls import path,include
from .views import create_order,webhook,payment_success

urlpatterns = [
    path('create-order/', create_order, name='create_order'),
    path('webhook/', webhook),
    path('success/', payment_success),
    
]