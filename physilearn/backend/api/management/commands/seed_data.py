from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Student, HealthRecord, HealthHistory, FitnessPerformance, TeacherSection, PESession, Attendance
from django.utils import timezone
from datetime import datetime, timedelta, time
import os
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Reset database and create seed data'

    def handle(self, *args, **options):
        # Load admin credentials from .env
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        User.objects.filter(role__in=['TEACHER', 'PARENT', 'ADMIN']).delete()
        Student.objects.all().delete()
        HealthRecord.objects.all().delete()
        HealthHistory.objects.all().delete()
        FitnessPerformance.objects.all().delete()
        TeacherSection.objects.all().delete()
        PESession.objects.all().delete()
        Attendance.objects.all().delete()
        
        # Create admin user from .env
        self.stdout.write('Creating admin user...')
        admin = User.objects.create_superuser(
            username=admin_username,
            email='admin@school.com',
            password=admin_password
        )
        # Explicitly set role to ADMIN (create_superuser doesn't set custom role field)
        admin.role = 'ADMIN'
        admin.save(update_fields=['role'])
        
        # Create teacher
        self.stdout.write('Creating teacher...')
        teacher = User.objects.create_user(
            username='teacher1',
            email='teacher1@school.com',
            password='password123',
            first_name='John',
            last_name='Smith',
            role='TEACHER'
        )
        
        # Create parents
        self.stdout.write('Creating parents...')
        parent1 = User.objects.create_user(
            username='parent1',
            email='parent1@email.com',
            password='password123',
            first_name='Alice',
            last_name='Johnson',
            role='PARENT'
        )
        
        parent2 = User.objects.create_user(
            username='parent2',
            email='parent2@email.com',
            password='password123',
            first_name='Bob',
            last_name='Williams',
            role='PARENT'
        )
        
        # Create students
        self.stdout.write('Creating 10 students...')
        section = 'Grade-10A'
        students = []
        
        # Parent 1 children (5 students)
        for i in range(1, 6):
            student = Student.objects.create(
                name=f'Student {i}',
                roll_number=f'2024-{i:03d}',
                section=section,
                parent=parent1
            )
            students.append(student)
            self.create_health_data(student)
        
        # Parent 2 children (5 students)
        for i in range(6, 11):
            student = Student.objects.create(
                name=f'Student {i}',
                roll_number=f'2024-{i:03d}',
                section=section,
                parent=parent2
            )
            students.append(student)
            self.create_health_data(student)
        
        # Assign teacher to section
        TeacherSection.objects.create(
            teacher=teacher,
            section=section
        )
        
        # Create some PE sessions
        self.stdout.write('Creating PE sessions...')
        for i in range(5):
            PESession.objects.create(
                name=f'PE Session {i+1}',
                date=timezone.now().date() - timedelta(days=i*7),
                section=section,
                teacher=teacher,
                description=f'Physical Education class {i+1}',
                start_time=time(9, 0),
                end_time=time(10, 0)
            )
        
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write('\nLogin credentials:')
        self.stdout.write(f'Admin: {admin_username} / {admin_password}')
        self.stdout.write('Teacher: teacher1 / password123')
        self.stdout.write('Parent 1: parent1 / password123')
        self.stdout.write('Parent 2: parent2 / password123')
    
    def create_health_data(self, student):
        """Create health records and fitness data for a student"""
        # Create health record
        height = random.uniform(150, 180)
        weight = random.uniform(50, 80)
        bmi = weight / ((height/100) ** 2)
        
        health_record = HealthRecord.objects.create(
            student=student,
            height=round(height, 1),
            weight=round(weight, 1),
            bmi=round(bmi, 1),
            fitness_status=self.get_fitness_status(bmi)
        )
        
        # Create health history (last 3 months)
        for days_ago in [90, 60, 30, 0]:
            hist_height = height + random.uniform(-2, 2)
            hist_weight = weight + random.uniform(-3, 3)
            hist_bmi = hist_weight / ((hist_height/100) ** 2)
            
            HealthHistory.objects.create(
                student=student,
                date=timezone.now().date() - timedelta(days=days_ago),
                height=round(hist_height, 1),
                weight=round(hist_weight, 1),
                bmi=round(hist_bmi, 1),
                fitness_status=self.get_fitness_status(hist_bmi)
            )
        
        # Create fitness performances
        metrics = ['Stamina', 'Strength', 'Flexibility', 'Agility', 'Speed']
        for metric in metrics:
            for days_ago in [60, 30, 0]:
                FitnessPerformance.objects.create(
                    student=student,
                    date=timezone.now().date() - timedelta(days=days_ago),
                    metric_name=metric,
                    score=random.randint(40, 95)
                )
    
    def get_fitness_status(self, bmi):
        """Get fitness status based on BMI"""
        if bmi < 18.5:
            return 'Underweight'
        elif bmi < 25:
            return 'Normal'
        elif bmi < 30:
            return 'Overweight'
        else:
            return 'Obese'
