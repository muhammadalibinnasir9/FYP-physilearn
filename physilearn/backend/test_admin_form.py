import os
import django
from django.test import Client
import re

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver']

from django.contrib.auth import get_user_model
User = get_user_model()

User.objects.filter(username="test_admin_mgmt").delete()
admin_user = User.objects.create_superuser("test_admin_mgmt", "admin@test.com", "password")

client = Client()
client.force_login(admin_user)

print("Fetching Add User Page...")
resp = client.get('/admin/api/user/add/')
inputs = re.findall(r'<input[^>]+name="([^"]+)"', resp.content.decode('utf-8'))
for inp in set(inputs):
    print("Input:", inp)
