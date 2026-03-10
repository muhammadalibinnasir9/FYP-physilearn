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

User = get_user_model()

# Setup test data
User.objects.filter(username__in=["struct_teacher", "struct_parent"]).delete()
teacher_user = User.objects.create_user(username="struct_teacher", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="struct_parent", password="password", role="PARENT")

Student.objects.filter(roll_number="STRUCT_123").delete()
student = Student.objects.create(name="Structure Test Student", roll_number="STRUCT_123", parent=parent_user, teacher=teacher_user)

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
        height=170,
        weight=65,
        fitness_test_scores={"pushups": 35, "situps": 40}
    )
    # The models calculate BMI automatically! Expected: ~22.49 (Normal), Recommendation: "Maintain your current balanced diet..."
    
    fp1 = FitnessPerformance.objects.create(
        student=student,
        metric_name="Endurance",
        score=75
    )
    
    print("--- GENERATING REPORT ---")
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    
    resp = client.get(f'/api/students/{student.id}/report/')
    print("Report endpoint status:", resp.status_code)
    
    if resp.status_code == 200:
        pdf_file = BytesIO(resp.content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
            
        print("--- VERIFYING REPORT CONTENT ---")
        
        # print(text)
        
        # Look for the 4 explicit functional requirements
        print_result("Structure Test Student" in text and "STRUCT_123" in text, "Report includes student information")
        print_result("22.49" in text, "Report includes BMI calculation metric")
        print_result("Endurance" in text and "170" in text, "Report includes fitness history (Historical Health/Performances)")
        print_result("Maintain your current balanced diet" in text, "Report includes AI health recommendations")
        
        # Save sample to disk
        with open('sample_report.pdf', 'wb') as f:
            f.write(resp.content)
         
except Exception as e:
    print(f"Error during report generation: {e}")
    overall_status = "FAIL"

print(f"\nFINAL VERIFICATION: {overall_status}")
print("Sample saved to sample_report.pdf")

# Cleanup
hr.delete()
fp1.delete()
Student.objects.filter(roll_number="STRUCT_123").delete()
teacher_user.delete()
parent_user.delete()
