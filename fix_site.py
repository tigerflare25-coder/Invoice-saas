import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_saas.settings')
django.setup()

from django.contrib.sites.models import Site

# This ensures Site ID 1 exists and matches your actual domain
domain = 'invoice-flow-drpu.onrender.com'
site, created = Site.objects.get_or_create(id=1)
site.domain = domain
site.name = 'InvoiceFlow'
site.save()

print(f"✅ Success: Site table updated to {domain}")
