import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from api.models import Student, HealthRecord
from django.contrib.auth import get_user_model

User = get_user_model()

# Setup test data
User.objects.filter(username__in=["bmi_teacher", "bmi_parent"]).delete()
teacher_user = User.objects.create_user(username="bmi_teacher", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="bmi_parent", password="password", role="PARENT")

Student.objects.filter(roll_number="BMI_123").delete()
student = Student.objects.create(name="BMI Test Student", roll_number="BMI_123", parent=parent_user, teacher=teacher_user)

overall_status = "PASS"

def print_result(condition, test_name):
    global overall_status
    if condition:
        print(f"PASS: {test_name}")
    else:
        print(f"FAIL: {test_name}")
        overall_status = "FAIL"

try:
    # Test data: Height = 1.70 m (170 cm), Weight = 65 kg
    # Expected BMI calculation: 65 / (1.70^2) = 65 / 2.89 = 22.4913...
    
    hr = HealthRecord.objects.create(
        student=student,
        height=170, # Backend expects height in cm judging by previous db persistence tests, let's verify models.py logic
        weight=65
    )
    
    print(f"Stored Height: {hr.height} cm")
    print(f"Stored Weight: {hr.weight} kg")
    print(f"Calculated BMI: {hr.bmi}")
    
    # Check if BMI is approx 22.49
    # The models.py rounds to 2 decimal places: round(w / (height_m ** 2), 2)
    expected_bmi = 22.49
    
    print_result(hr.bmi is not None, "System calculates BMI automatically")
    print_result(hr.bmi == expected_bmi, f"BMI calculation matches expected value ({expected_bmi})")

except Exception as e:
    print(f"Error during test: {e}")
    overall_status = "FAIL"

print(f"\nFINAL VERIFICATION: {overall_status}")

# Cleanup
hr.delete()
Student.objects.filter(roll_number="BMI_123").delete()
teacher_user.delete()
parent_user.delete()
