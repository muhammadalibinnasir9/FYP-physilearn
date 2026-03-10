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
User.objects.filter(username__in=["mod_admin", "mod_teacher", "mod_parent"]).delete()
admin_user = User.objects.create_user(username="mod_admin", password="password", role="ADMIN")
teacher_user = User.objects.create_user(username="mod_teacher", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="mod_parent", password="password", role="PARENT")

Student.objects.filter(roll_number="MOD_123").delete()
student = Student.objects.create(name="Mod Test Student", roll_number="MOD_123", parent=parent_user, teacher=teacher_user)

overall_status = "PASS"

def print_result(condition, test_name):
    global overall_status
    if condition:
        print(f"PASS: {test_name}")
    else:
        print(f"FAIL: {test_name}")
        overall_status = "FAIL"

try:
    client = APIClient()
    
    # 1. Parent - NOT allowed to edit
    client.force_authenticate(user=parent_user)
    resp_parent = client.patch(f'/api/students/{student.id}/', data={"name": "Parent Hack"}, format='json')
    print_result(resp_parent.status_code == 403, "Parent blocked from modifying Student record")
    
    # 2. Teacher - allowed to edit (their assigned students)
    client.force_authenticate(user=teacher_user)
    resp_teacher = client.patch(f'/api/students/{student.id}/', data={"section": "Teacher Section"}, format='json')
    print_result(resp_teacher.status_code == 200, "Teacher allowed to modify assigned Student record")
    student.refresh_from_db()
    
    # 3. Admin - allowed to edit
    client.force_authenticate(user=admin_user)
    resp_admin = client.patch(f'/api/students/{student.id}/', data={"section": "Admin Section"}, format='json')
    print_result(resp_admin.status_code == 200, "Admin allowed to modify Student record")

except Exception as e:
    print(f"Error during test: {e}")
    overall_status = "FAIL"

print(f"\nFINAL VERIFICATION: {overall_status}")

# Cleanup
Student.objects.filter(roll_number="MOD_123").delete()
admin_user.delete()
teacher_user.delete()
parent_user.delete()
