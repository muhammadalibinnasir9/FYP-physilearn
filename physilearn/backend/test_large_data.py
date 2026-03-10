import os
import django
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "physilearn_backend.settings")
django.setup()

from api.models import User, Student, HealthRecord, FitnessPerformance

def seed_large_data(count=100):
    print(f"--- SEEDING {count} STUDENTS ---")
    start_time = time.time()
    
    # Get or create teacher/parent
    teacher, _ = User.objects.get_or_create(username="perf_teacher", defaults={"role": "TEACHER"})
    teacher.set_password("password123")
    teacher.save()
    
    parent, _ = User.objects.get_or_create(username="perf_parent", defaults={"role": "PARENT"})
    parent.set_password("password123")
    parent.save()

    students_to_create = []
    for i in range(count):
        students_to_create.append(Student(
            name=f"Student {i}",
            roll_number=f"R-{i}",
            section="A",
            parent=parent,
            teacher=teacher
        ))
    
    Student.objects.bulk_create(students_to_create)
    created_students = Student.objects.filter(teacher=teacher)
    
    hr_to_create = []
    for s in created_students:
        hr_to_create.append(HealthRecord(
            student=s,
            height=160.0 + (s.id % 20),
            weight=50.0 + (s.id % 30),
            activity_record="Physical Education"
        ))
    HealthRecord.objects.bulk_create(hr_to_create)

    end_time = time.time()
    print(f"SUCCESS: Seeded {count} students and health records in {end_time - start_time:.2f}s")

if __name__ == "__main__":
    # Clean up first
    Student.objects.filter(name__startswith="Student ").delete()
    seed_large_data(200) # Seeding 200 for a solid performance check
