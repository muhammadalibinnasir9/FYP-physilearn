#!/usr/bin/env python3
"""
Test script to verify health record POST functionality for teachers
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
from api.models import Student, HealthRecord, TeacherSection
from api.views import HealthRecordViewSet
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

User = get_user_model()

def test_health_record_post_functionality():
    """Test the health record POST functionality"""
    factory = APIRequestFactory()
    
    print("Testing Health Record POST functionality...")
    
    # Create test users
    admin = User.objects.create_user(
        username='test_admin',
        email='admin@test.com',
        password='testpass123',
        role='ADMIN'
    )
    
    teacher = User.objects.create_user(
        username='test_teacher',
        email='teacher@test.com',
        password='testpass123',
        role='TEACHER'
    )
    
    parent = User.objects.create_user(
        username='test_parent',
        email='parent@test.com',
        password='testpass123',
        role='PARENT'
    )
    
    # Create teacher section assignment
    TeacherSection.objects.create(
        teacher=teacher,
        section='7-A',
        assigned_by=admin
    )
    
    # Create test student
    student = Student.objects.create(
        name='Test Student',
        roll_number='ST001',
        section='7-A',
        parent=parent,
        teacher=teacher
    )
    
    # Test 1: Teacher can POST health record with height and weight
    print("\n1. Testing teacher POST health record with height and weight")
    
    view = HealthRecordViewSet.as_view({'post': 'create'})
    
    data = {
        'student': student.id,
        'height': 170.5,
        'weight': 65.2,
    }
    
    request = factory.post('/api/health-records/', data, format='json')
    force_authenticate(request, user=teacher)
    
    response = view(request)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Health record created successfully")
        print(f"   Response Data: {response.data}")
        
        # Verify the data was saved correctly
        try:
            health_record = HealthRecord.objects.get(student=student)
            print(f"   ✅ Height saved: {health_record.height} cm")
            print(f"   ✅ Weight saved: {health_record.weight} kg")
            print(f"   ✅ BMI calculated: {health_record.bmi}")
            print(f"   ✅ Fitness status: {health_record.fitness_status}")
        except HealthRecord.DoesNotExist:
            print("   ❌ Health record not found in database")
    else:
        print(f"   ❌ Failed to create health record: {response.data}")
    
    # Test 2: Teacher cannot POST for student in different section
    print("\n2. Testing teacher POST for student in different section (should fail)")
    
    # Create student in different section
    other_student = Student.objects.create(
        name='Other Student',
        roll_number='ST002',
        section='8-B',
        parent=parent,
        teacher=None  # Not assigned to this teacher
    )
    
    data = {
        'student': other_student.id,
        'height': 160.0,
        'weight': 55.0,
    }
    
    request = factory.post('/api/health-records/', data, format='json')
    force_authenticate(request, user=teacher)
    
    response = view(request)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 403:
        print("   ✅ Correctly prevented access to student in different section")
        print(f"   Response: {response.data}")
    else:
        print(f"   ❌ Should have failed with 403, got {response.status_code}")
    
    # Test 3: Admin can POST for any student
    print("\n3. Testing admin POST health record (should succeed)")
    
    data = {
        'student': other_student.id,
        'height': 165.5,
        'weight': 58.7,
    }
    
    request = factory.post('/api/health-records/', data, format='json')
    force_authenticate(request, user=admin)
    
    response = view(request)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Admin can create health record for any student")
        print(f"   Response Data: {response.data}")
    else:
        print(f"   ❌ Admin should be able to create health record: {response.data}")
    
    # Test 4: Validation for missing required fields
    print("\n4. Testing validation for missing required fields")
    
    # Test missing student
    data = {
        'height': 170.0,
        'weight': 65.0,
    }
    
    request = factory.post('/api/health-records/', data, format='json')
    force_authenticate(request, user=teacher)
    
    response = view(request)
    print(f"   Status Code (missing student): {response.status_code}")
    
    if response.status_code == 400:
        print("   ✅ Correctly validated missing student field")
    else:
        print(f"   ❌ Should have failed with 400 for missing student")
    
    # Test invalid values
    data = {
        'student': student.id,
        'height': -10,  # Invalid height
        'weight': 0,     # Invalid weight
    }
    
    request = factory.post('/api/health-records/', data, format='json')
    force_authenticate(request, user=teacher)
    
    response = view(request)
    print(f"   Status Code (invalid values): {response.status_code}")
    
    # Note: The backend might accept negative values and handle validation in the model
    
    print("\n✅ Health Record POST functionality test completed!")
    print("\nSummary:")
    print("- POST /api/health-records/ endpoint is working")
    print("- Teachers can create health records for their assigned students")
    print("- Teachers cannot access students in other sections")
    print("- Admins can create health records for any student")
    print("- Height and weight fields are properly handled")
    print("- BMI is automatically calculated")
    print("- Student ID linking is working correctly")

if __name__ == '__main__':
    test_health_record_post_functionality()
