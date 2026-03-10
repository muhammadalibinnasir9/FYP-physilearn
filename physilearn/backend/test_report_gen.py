import os
import django
import PyPDF2
from io import BytesIO

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from rest_framework.test import APIClient
from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver']

from django.contrib.auth import get_user_model
from api.models import Student, HealthRecord, FitnessPerformance, HealthHistory
import time

User = get_user_model()

# Setup test data
User.objects.filter(username__in=["report_teacher", "report_parent"]).delete()
teacher_user = User.objects.create_user(username="report_teacher", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="report_parent", password="password", role="PARENT")

Student.objects.filter(roll_number="REPORT_123").delete()
student = Student.objects.create(name="Report Test Student", roll_number="REPORT_123", parent=parent_user, teacher=teacher_user)

overall_status = "PASS"

def print_result(condition, test_name):
    global overall_status
    if condition:
        print(f"PASS: {test_name}")
    else:
        print(f"FAIL: {test_name}")
        overall_status = "FAIL"

try:
    print("--- INSERTING HISTORICAL DATA ---")
    hr = HealthRecord.objects.create(
        student=student,
        height=150,
        weight=50,
        fitness_test_scores={"pushups": 15, "situps": 20}
    )
    # Simulate a change over time
    hr.height = 155
    hr.weight = 52
    hr.fitness_test_scores = {"pushups": 25, "situps": 30}
    hr.save()
    
    fp1 = FitnessPerformance.objects.create(
        student=student,
        metric_name="Endurance",
        score=70
    )
    
    fp2 = FitnessPerformance.objects.create(
        student=student,
        metric_name="Endurance",
        score=85
    )
    
    print("--- GENERATING REPORT ---")
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    
    resp = client.get(f'/api/students/{student.id}/report/')
    print("Report endpoint status:", resp.status_code)
    
    print_result(resp.status_code == 200, "Teacher can access report generation endpoint")
    print_result(resp['Content-Type'] == 'application/pdf', "Response is a valid PDF")
    
    if resp.status_code == 200:
        pdf_file = BytesIO(resp.content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
            
        print("--- VERIFYING REPORT CONTENT ---")
        
        # Look for fitness metrics and historical changes
        # e.g., the student's name, height, weight, BMI, scores, history
        print_result("Report Test Student" in text, "Report includes student name")
        print_result("150" in text and "155" in text, "Report includes historical HealthHistory data (height)")
        print_result("70" in text and "85" in text, "Report includes historical FitnessPerformance data (Endurance)")
        print_result("Endurance" in text, "Report includes Fitness Metrics")
        
        # print(text)
         
except Exception as e:
    print(f"Error during report generation: {e}")
    overall_status = "FAIL"

print(f"\nFINAL VERIFICATION: {overall_status}")

# Cleanup
hr.delete()
fp1.delete()
fp2.delete()
Student.objects.filter(roll_number="REPORT_123").delete()
teacher_user.delete()
parent_user.delete()
