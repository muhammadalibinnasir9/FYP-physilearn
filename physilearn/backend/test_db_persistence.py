import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from api.models import Student, HealthRecord, FitnessPerformance, HealthHistory
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Setup test data
User.objects.filter(username__in=["db_teacher", "db_parent"]).delete()
teacher_user = User.objects.create_user(username="db_teacher", password="password", role="TEACHER")
parent_user = User.objects.create_user(username="db_parent", password="password", role="PARENT")

Student.objects.filter(roll_number="DB_TEST_123").delete()
student = Student.objects.create(name="DB Test Student", roll_number="DB_TEST_123", parent=parent_user, teacher=teacher_user)

overall_status = "PASS"

def print_result(condition, test_name):
    global overall_status
    if condition:
        print(f"PASS: {test_name}")
    else:
        print(f"FAIL: {test_name}")
        overall_status = "FAIL"

print("--- VERIFYING SCHEMA / FIELDS ---")
# Fields are verified implicitly by usage, but let's confirm the attributes exist
# HealthRecord: student_id, height, weight, bmi, fitness_test_scores, updated_at
# FitnessPerformance: student_id, metric_name, score, date

try:
    print("--- INSERTING TEST DATA ---")
    hr = HealthRecord.objects.create(
        student=student,
        height=160,
        weight=60,
        fitness_test_scores={"pushups": 30, "situps": 40}
    )
    # The custom save method on HealthRecord calculates bmi and creates a HealthHistory entry
    
    fp = FitnessPerformance.objects.create(
        student=student,
        metric_name="Endurance",
        score=85.5
    )
    
    print("--- CONFIRMING PERSISTENCE ---")
    
    hr_db = HealthRecord.objects.get(student=student)
    print_result(hr_db.height == 160, "HealthRecord height saved")
    print_result(hr_db.weight == 60, "HealthRecord weight saved")
    print_result(hr_db.bmi is not None, f"HealthRecord BMI calculated and saved: {hr_db.bmi}")
    print_result(hr_db.fitness_test_scores == {"pushups": 30, "situps": 40}, "HealthRecord fitness results saved")
    print_result(hr_db.updated_at is not None, f"HealthRecord timestamp saved: {hr_db.updated_at}")
    
    fp_db = FitnessPerformance.objects.get(student=student, metric_name="Endurance")
    print_result(fp_db.score == 85.5, "FitnessPerformance score saved")
    print_result(fp_db.date is not None, f"FitnessPerformance timestamp (date) saved: {fp_db.date}")
    
    hh_db = HealthHistory.objects.filter(student=student).first()
    print_result(hh_db is not None, "HealthHistory (timestamped log) entry saved by custom signal/logic")
    if hh_db:
         print_result(hh_db.bmi == hr_db.bmi, "HealthHistory BMI matches")
         
except Exception as e:
    print(f"Error during database operations: {e}")
    overall_status = "FAIL"

print(f"\nFINAL VERIFICATION: {overall_status}")

# Cleanup
hr.delete()
fp.delete()
Student.objects.filter(roll_number="DB_TEST_123").delete()
teacher_user.delete()
parent_user.delete()
