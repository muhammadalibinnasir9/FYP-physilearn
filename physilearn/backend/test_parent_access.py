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
User.objects.filter(username__in=["report_parent2", "report_teacher2"]).delete()
teacher_user = User.objects.create_user(username="report_teacher2", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="report_parent2", password="password", role="PARENT")

Student.objects.filter(roll_number="PARENT_123").delete()
student = Student.objects.create(name="Parent Test Student", roll_number="PARENT_123", parent=parent_user, teacher=teacher_user)

hr = HealthRecord.objects.create(
    student=student,
    height=150,
    weight=50,
    fitness_test_scores={"pushups": 15, "situps": 20}
)

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
    
    # 1. Parent login
    # Rather than hitting the JWT endpoint directly, force_authenticate achieves the same token-equivalent context in testing DRF views
    client.force_authenticate(user=parent_user)
    
    # 2. Access student report page
    resp_report = client.get(f'/api/students/{student.id}/report/')
    
    # Check parent can view reports
    print_result(resp_report.status_code == 200, "Parent can view report endpoint")
    print_result(resp_report['Content-Type'] == 'application/pdf', "Parent receives a valid PDF report")
    
    # 3. Confirm parent cannot edit or modify records
    # Test PATCH to student endpoint
    resp_patch_student = client.patch(f'/api/students/{student.id}/', data={"name": "Hacked Student"}, format='json')
    print_result(resp_patch_student.status_code == 403, "Parent blocked from modifying Student record (PATCH)")
    
    # Test PATCH to HealthRecord endpoint
    resp_patch_hr = client.patch(f'/api/health-records/{hr.id}/', data={"height": 999}, format='json')
    print_result(resp_patch_hr.status_code == 403, "Parent blocked from modifying HealthRecord (PATCH)")
    
    # Test POST to FitnessPerformance endpoint
    resp_post_perf = client.post('/api/fitness-performances/', data={
        "student": student.id,
        "metric_name": "Pushups",
        "score": 100
    }, format='json')
    print_result(resp_post_perf.status_code == 403, "Parent blocked from creating FitnessPerformance (POST)")
    
    # Finally, ensure they CAN read the list endpoint if needed (StudentListView filtering tests already handled it, though)
    resp_student_detail = client.get(f'/api/students/{student.id}/')
    print_result(resp_student_detail.status_code == 200, "Parent can view (read) their own student API details")

except Exception as e:
    print(f"Error during test: {e}")
    overall_status = "FAIL"

print(f"\nFINAL VERIFICATION: {overall_status}")

# Cleanup
hr.delete()
Student.objects.filter(roll_number="PARENT_123").delete()
teacher_user.delete()
parent_user.delete()
