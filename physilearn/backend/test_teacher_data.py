import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from rest_framework.test import APIClient
from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver']

from django.contrib.auth import get_user_model
from api.models import Student, HealthRecord, FitnessPerformance

User = get_user_model()

# Setup test data
User.objects.filter(username__in=["teacher_data_mgmt", "parent_test1"]).delete()
teacher_user = User.objects.create_user(username="teacher_data_mgmt", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="parent_test1", password="password", role="PARENT")

student = Student.objects.create(name="Data Test Student", roll_number="999", parent=parent_user, teacher=teacher_user)
# Ensure no health record exists for creation test
HealthRecord.objects.filter(student=student).delete()
FitnessPerformance.objects.filter(student=student).delete()

client = APIClient()
client.force_authenticate(user=teacher_user)

overall_status = "PASS"

def print_result(condition, test_name):
    global overall_status
    if condition:
        print(f"PASS: {test_name}")
    else:
        print(f"FAIL: {test_name}")
        overall_status = "FAIL"

# --- Test 1: Teacher creates HealthRecord
payload = {
    "student": student.id,
    "height": 155,
    "weight": 52,
    "activity_record": "Running",
    "fitness_test_scores": {"pushups": 20}
}
resp = client.post('/api/health-records/', data=payload, format='json')

print("Create HealthRecord status:", resp.status_code)
if resp.status_code != 201:
    print("Response Data:", resp.data)

print_result(resp.status_code == 201, "Teacher can submit (create) health data for their assigned student")

if resp.status_code == 201:
    hr_id = resp.data.get('id')
    # Use hr_id if available, otherwise fetch from db
    if not hr_id:
        hr_id = HealthRecord.objects.get(student=student).id
    
    # --- Test 2: Teacher updates HealthRecord
    resp_patch = client.patch(f'/api/health-records/{hr_id}/', data={"height": 160}, format='json')
    print("Update HealthRecord status:", resp_patch.status_code)
    if resp_patch.status_code != 200:
        print("Response Data:", resp_patch.data)
    print_result(resp_patch.status_code == 200, "Teacher can update health data for their assigned student")

# --- Test 3: Teacher creates FitnessPerformance
perf_payload = {
    "student": student.id,
    "metric_name": "Pushups",
    "score": 40
}
resp_perf = client.post('/api/fitness-performances/', data=perf_payload, format='json')

print("Create FitnessPerformance status:", resp_perf.status_code)
if resp_perf.status_code != 201:
    print("Response Data:", resp_perf.data)
print_result(resp_perf.status_code == 201, "Teacher can submit fitness performance for their assigned student")

print(f"\nFINAL VERIFICATION: {overall_status}")
