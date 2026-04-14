from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField

class User(AbstractUser):
    # Make email unique so Allauth can use it as the primary ID
    email = models.EmailField(unique=True)
    is_premium = models.BooleanField(default=False)
    logo = CloudinaryField('image', null=True, blank=True)

    # USERNAME_FIELD is 'username' by default. 
    # REQUIRED_FIELDS must NOT include 'username' for auto-signup to work smoothly.
    REQUIRED_FIELDS = [] 

    def __str__(self):
        return self.email
    
    