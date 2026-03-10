from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import User, Student, HealthRecord
from rest_framework import status

class HealthLogicTest(TestCase):
    def setUp(self):
        self.parent = User.objects.create_user(username='parent', password='password', role='PARENT')
        self.student = Student.objects.create(name='Test Student', roll_number='TEST001', parent=self.parent)

    def test_bmi_calculation_accuracy(self):
        """Verify that BMI is calculated correctly: BMI = weight / (height/100)^2"""
        # Case: Height 170cm, Weight 70kg -> BMI 24.22
        hr = HealthRecord.objects.create(student=self.student, height=170, weight=70, activity_record="Test")
        self.assertEqual(hr.bmi, 24.22)
        self.assertEqual(hr.fitness_status, "Normal")

        # Case: Height 160cm, Weight 90kg -> BMI 35.16
        hr.height = 160
        hr.weight = 90
        hr.save()
        self.assertEqual(hr.bmi, 35.16)
        self.assertEqual(hr.fitness_status, "Obese")

    def test_impossible_data_rejection(self):
        """Ensure system rejects negative height or weight."""
        with self.assertRaises(ValidationError):
            HealthRecord.objects.create(student=self.student, height=-170, weight=70, activity_record="Test")
        
        with self.assertRaises(ValidationError):
            HealthRecord.objects.create(student=self.student, height=170, weight=0, activity_record="Test")

class SecurityAuditTest(TestCase):
    def setUp(self):
        self.parent1 = User.objects.create_user(username='parent1', password='password', role='PARENT')
        self.parent2 = User.objects.create_user(username='parent2', password='password', role='PARENT')
        
        self.child1 = Student.objects.create(name='Child 1', roll_number='C001', parent=self.parent1)
        self.child2 = Student.objects.create(name='Child 2', roll_number='C002', parent=self.parent2)
        
        self.client = Client()

    def test_unauthorized_access_prevention(self):
        """Verify Parent 1 cannot access Parent 2's child data via API."""
        # Get JWT for Parent 1
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'parent1',
            'password': 'password'
        })
        token = response.data['access']
        header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

        # Try to access Parent 2's child detail
        url = reverse('student_detail', kwargs={'pk': self.child2.pk})
        response = self.client.get(url, **header)
        
        # Result should be 403 Forbidden or 404 Not Found depending on implementation
        # our IsOwnerOrStaff returns False, so 403
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_access_allowed(self):
        """Verify Parent 1 CAN access their own child data."""
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'parent1',
            'password': 'password'
        })
        token = response.data['access']
        header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

        url = reverse('student_detail', kwargs={'pk': self.child1.pk})
        response = self.client.get(url, **header)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Child 1')

class BusinessRulesTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='password', role='TEACHER')
        self.parent = User.objects.create_user(username='parent', password='password', role='PARENT')
        self.student = Student.objects.create(name='Student', roll_number='S1', parent=self.parent, teacher=self.teacher)
        self.hr = HealthRecord.objects.create(student=self.student, height=170, weight=70, activity_record="Test")
        self.client = Client()

    def get_token(self, username):
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': username,
            'password': 'password'
        })
        return response.data['access']

    def test_parent_read_only(self):
        """Verify Parent cannot update data even for their own child."""
        token = self.get_token('parent')
        header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        url = reverse('student_detail', kwargs={'pk': self.student.pk})
        
        # PATCH attempt
        response = self.client.patch(url, {'name': 'New Name'}, content_type='application/json', **header)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_write_access(self):
        """Verify Teacher can update their assigned student's data."""
        token = self.get_token('teacher')
        header = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        url = reverse('student_detail', kwargs={'pk': self.student.pk})
        
        # PATCH attempt
        response = self.client.patch(url, {'name': 'Updated Name'}, content_type='application/json', **header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.name, 'Updated Name')

