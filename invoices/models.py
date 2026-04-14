from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.db import models
from django.conf import settings


class Invoice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField(blank=True, null=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_amount(self):
        items = self.items.all()
        subtotal = sum(item.total_price() for item in items)
        tax = (subtotal * self.tax_percentage) / 100
        return subtotal + tax

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.quantity * self.unit_price