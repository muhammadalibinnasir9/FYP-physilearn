from api.models import Student
students = Student.objects.all()
print(f"Total students: {len(students)}")
for s in students:
    print(f"ID: {s.id} | Name: {s.name} | Parent: {s.parent.username}")
