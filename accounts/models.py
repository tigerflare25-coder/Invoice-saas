from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField

from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
from django.utils import timezone # Add this for time calculations

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_premium = models.BooleanField(default=False)
    # New Field: Track when the subscription ends
    premium_expiry = models.DateTimeField(null=True, blank=True) 
    logo = CloudinaryField('image', null=True, blank=True)

    REQUIRED_FIELDS = [] 

    def check_premium_status(self):
        """
        Call this in your views/templates to see if user is STILL pro.
        If the current time is past expiry, it flips them to False.
        """
        if self.is_premium and self.premium_expiry:
            if timezone.now() > self.premium_expiry:
                self.is_premium = False
                self.save()
        return self.is_premium

    def __str__(self):
        return self.email
    
    
