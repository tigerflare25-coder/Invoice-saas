from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.db import models
from django.conf import settings


from django.db import models
from django.conf import settings

class Invoice(models.Model):

    TEMPLATE_CHOICES = [
        ('minimal', 'Minimal'),
        ('gst', 'GST India'),
        ('premium', 'Premium'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # CLIENT INFO
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField(blank=True, null=True)

    # MONEY
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # 🔥 NEW FIELDS (IMPORTANT)
    template = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='minimal')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_link = models.URLField(blank=True, null=True)

    # DATES
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(blank=True, null=True)

    def subtotal(self):
        return sum(item.total_price() for item in self.items.all())

    def tax_amount(self):
        return (self.subtotal() * self.tax_percentage) / 100

    def total_amount(self):
        return self.subtotal() + self.tax_amount()

    def __str__(self):
        return f"Invoice #{self.id} - {self.client_name}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return self.description
