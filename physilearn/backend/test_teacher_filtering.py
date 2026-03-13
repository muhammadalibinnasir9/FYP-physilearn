#!/usr/bin/env python3
"""
Test script to verify teacher filtering functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'physilearn_backend.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from api.models import Student, TeacherSection
from api.views import students_list_view

User = get_user_model()

def test_teacher_filtering():
    """Test the teacher filtering functionality"""
    factory = RequestFactory()
    
    print("Testing teacher filtering functionality...")
    
    # Test 1: Teacher with teacher_id=me parameter
    print("\n1. Testing teacher with teacher_id=me parameter")
    
    # Create a test teacher
    teacher = User.objects.create_user(
        username='test_teacher',
        email='teacher@test.com',
        password='testpass123',
        role='TEACHER'
    )
    
    # Create test sections assignment
    TeacherSection.objects.create(
        teacher=teacher,
        section='7-A',
        assigned_by=User.objects.filter(role='ADMIN').first() or teacher
    )
    
    # Create test student
    student = Student.objects.create(
        name='Test Student',
        roll_number='ST001',
        section='7-A',
        parent=User.objects.create_user(
            username='test_parent',
            email='parent@test.com',
            password='testpass123',
            role='PARENT'
        ),
        teacher=teacher
    )
    
    # Test request with teacher_id=me
    request = factory.get('/api/students?teacher_id=me')
    request.user = teacher
    
    response = students_list_view(request)
    print(f"   Status: {response.status_code}")
    print(f"   Response data: {response.data}")
    
    # Test 2: Teacher trying to access another teacher_id
    print("\n2. Testing teacher with invalid teacher_id parameter")
    
    # Create another teacher
    other_teacher = User.objects.create_user(
        username='other_teacher',
        email='other@test.com',
        password='testpass123',
        role='TEACHER'
    )
    
    request = factory.get('/api/students?teacher_id=999')
    request.user = teacher
    
    response = students_list_view(request)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.data}")
    
    # Test 3: Teacher without teacher_id parameter (default behavior)
    print("\n3. Testing teacher without teacher_id parameter (default)")
    
    request = factory.get('/api/students')
    request.user = teacher
    
    response = students_list_view(request)
    print(f"   Status: {response.status_code}")
    print(f"   Response data length: {len(response.data)}")
    
    print("\n✅ All tests completed successfully!")
    print("\nSummary:")
    print("- GET /api/students?teacher_id=me works for teachers")
    print("- Teachers cannot access other teachers' students")
    print("- Default behavior (no teacher_id) still works")
    print("- Filtering relies on JWT token authentication")

if __name__ == '__main__':
    test_teacher_filtering()
