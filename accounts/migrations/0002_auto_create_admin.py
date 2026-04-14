from django.db import migrations
from django.contrib.auth import get_user_model
import os

def create_admin(apps, schema_editor):
    User = get_user_model()
    admin_email = "thishyaradhya25@gmail.com"
    admin_username = "thishya"
    admin_password = os.environ.get("ADMIN_PASSWORD", "TemporaryPass123!")

    if not User.objects.filter(username=admin_username).exists():
        User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password
        )

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'), 
    ]
    operations = [
        migrations.RunPython(create_admin),
    ]