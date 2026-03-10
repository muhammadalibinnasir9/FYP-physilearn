import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from rest_framework.test import APIClient
from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver']

from django.contrib.auth import get_user_model
from api.models import Student

User = get_user_model()

# Setup test data
User.objects.filter(username__in=["test_admin", "test_teacher", "test_parent"]).delete()

admin_user = User.objects.create_user(username="test_admin", password="password", role="ADMIN", is_staff=True, is_superuser=True)
teacher_user = User.objects.create_user(username="test_teacher", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="test_parent", password="password", role="PARENT")

student = Student.objects.create(name="Test Student", roll_number="123", parent=parent_user, teacher=teacher_user)

client = APIClient()

overall_status = "PASS"

f = open("test_rbac_results.txt", "w")

def print_result(condition, test_name):
    global overall_status
    if condition:
        f.write(f"PASS: {test_name}\n")
    else:
        f.write(f"FAIL: {test_name}\n")
        overall_status = "FAIL"

# --- Test 1: Teacher should NOT access admin panel
# For standard Django views like admin, we might need a regular client with force_login, or we can just try to hit an Api endpoint
client.force_authenticate(user=teacher_user)
# Wait, admin panel uses session auth, APIClient force_authenticate might not work for /admin/. Let's authenticate using DRF for DRF endpoints.
# For admin, we can still use APIClient but with force_login since APIClient inherits from Client.
client.force_login(user=teacher_user)
resp = client.get('/admin/')
# Usually redirects to login if not staff, or 403
print_result(resp.status_code in [302, 403], "Teacher blocked from admin panel")

# --- Test 2: Teacher should NOT access user management via API (assuming standard DRF endpoints don't expose this except Admin)
# Wait, user management might be the admin panel itself, or maybe a /api/users endpoint?
# In urls.py there's no /api/users/ besides register. So admin panel user management is the main one.
resp = client.get('/admin/auth/user/')
print_result(resp.status_code in [302, 403], "Teacher blocked from user management (admin)")

# --- Test 3: Parent should NOT access student record editing
client.force_authenticate(user=parent_user)
resp = client.patch(f'/api/students/{student.id}/', content_type='application/json', data=json.dumps({"name": "Edited Student"}))
print_result(resp.status_code == 403, "Parent blocked from editing student record")
resp = client.put(f'/api/students/{student.id}/', content_type='application/json', data=json.dumps({"name": "Edited Student", "parent": parent_user.id}))
print_result(resp.status_code == 403, "Parent blocked from putting student record")

# Admin panel is standard Django, API endpoints are DRF
client.force_login(user=admin_user)
resp = client.get('/admin/api/user/')
if resp.status_code not in [200, 302]: # 302 sometimes means redirecting to real user model if needed
    print("Admin user mgmt resp stats:", resp.status_code)
print_result(resp.status_code in [200, 302], "Admin can access user management via admin panel")

resp = client.get('/admin/')
if resp.status_code != 200:
    print("Admin panel index resp:", resp.status_code)
print_result(resp.status_code == 200, "Admin can access system settings (admin panel index)")

f.write(f"\nFINAL VERIFICATION: {overall_status}\n")
f.close()

# Cleanup
student.delete()
admin_user.delete()
teacher_user.delete()
parent_user.delete()
