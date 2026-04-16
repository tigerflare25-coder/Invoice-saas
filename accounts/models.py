from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
from django.utils import timezone


class User(AbstractUser):
    # ─────────────────────────────
    # AUTH CORE
    # ─────────────────────────────
    email = models.EmailField(unique=True)
    REQUIRED_FIELDS = []

    # ─────────────────────────────
    # SUBSCRIPTION SYSTEM
    # ─────────────────────────────
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(null=True, blank=True)

    # (future ready for Cashfree / Stripe)
    subscription_id = models.CharField(max_length=255, blank=True, null=True)
    plan_name = models.CharField(max_length=50, default="free")  # free / pro

    # ─────────────────────────────
    # BUSINESS INFO (🔥 CRITICAL)
    # ─────────────────────────────
    company_name = models.CharField(max_length=255, blank=True)
    company_address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=50, blank=True)

    # ─────────────────────────────
    # PAYMENT SYSTEM
    # ─────────────────────────────
    payment_link = models.URLField(blank=True)  # Cashfree / UPI / Stripe

    # ─────────────────────────────
    # INVOICE DEFAULTS (🔥 UX BOOST)
    # ─────────────────────────────
    default_tax = models.FloatField(default=0)
    due_days = models.IntegerField(default=7)
    currency = models.CharField(max_length=10, default="₹")

    # ─────────────────────────────
    # BRANDING
    # ─────────────────────────────
    logo = CloudinaryField('image', null=True, blank=True)

    # ─────────────────────────────
    # ANALYTICS (future scaling)
    # ─────────────────────────────
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invoice_count = models.IntegerField(default=0)

    # ─────────────────────────────
    # SYSTEM
    # ─────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)

    # ─────────────────────────────
    # METHODS
    # ─────────────────────────────
    def check_premium_status(self):
        """
        Auto downgrade if subscription expired
        """
        if self.is_premium and self.premium_expiry:
            if timezone.now() > self.premium_expiry:
                self.is_premium = False
                self.plan_name = "free"
                self.save(update_fields=["is_premium", "plan_name"])
        return self.is_premium

    def is_pro(self):
        """
        Cleaner check in templates
        """
        return self.check_premium_status()

    def __str__(self):
        return self.email
    
    
