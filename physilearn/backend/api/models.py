from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError


class User(AbstractUser):
    ADMIN = 'ADMIN'
    TEACHER = 'TEACHER'
    PARENT = 'PARENT'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (TEACHER, 'Teacher'),
        (PARENT, 'Parent'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=PARENT)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class Student(models.Model):
    name = models.CharField(max_length=255)
    roll_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    section = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='children', limit_choices_to={'role': 'PARENT'})
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='students', limit_choices_to={'role': 'TEACHER'})

    class Meta:
        indexes = [
            models.Index(fields=['section']),
            models.Index(fields=['teacher']),
            models.Index(fields=['section', 'teacher']),
        ]

    def __str__(self):
        return f"{self.name} ({self.roll_number})"


class TeacherSection(models.Model):
    """Explicit mapping of teachers to sections/classes they are assigned to"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_sections', limit_choices_to={'role': 'TEACHER'})
    section = models.CharField(max_length=50, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='section_assignments', limit_choices_to={'role': 'ADMIN'})

    class Meta:
        unique_together = ['teacher', 'section']
        ordering = ['section']

    def __str__(self):
        return f"{self.teacher.username} - {self.section}"


class AcademicTerm(models.Model):
    name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date', 'name']

    def __str__(self):
        return self.name


class FitnessTestParameter(models.Model):
    term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fitness_parameters',
    )
    metric_name = models.CharField(max_length=100)
    passing_score = models.FloatField()
    max_score = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('term', 'metric_name')
        ordering = ['metric_name']

    def __str__(self):
        if self.term:
            return f"{self.metric_name} ({self.term.name})"
        return self.metric_name

from .ai_logic import classify_bmi, generate_recommendations
from .encryption import encrypt_value, decrypt_value

class HealthRecord(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='health_record')
    _height = models.TextField(db_column='height', help_text="Encrypted Height")
    _weight = models.TextField(db_column='weight', help_text="Encrypted Weight")
    _bmi = models.TextField(db_column='bmi', null=True, blank=True, help_text="Encrypted BMI")

    fitness_status = models.CharField(max_length=50, null=True, blank=True)
    ai_recommendations = models.TextField(null=True, blank=True)
    activity_record = models.TextField(null=True, blank=True, help_text="Record of physical activities")

    fitness_test_scores = models.JSONField(default=dict, help_text="Store scores as a JSON object")
    updated_at = models.DateTimeField(auto_now=True, db_index=True)


    @property
    def height(self):
        val = decrypt_value(self._height)
        return float(val) if val else None

    @height.setter
    def height(self, value):
        self._height = encrypt_value(value)

    @property
    def weight(self):
        val = decrypt_value(self._weight)
        return float(val) if val else None

    @weight.setter
    def weight(self, value):
        self._weight = encrypt_value(value)

    @property
    def bmi(self):
        val = decrypt_value(self._bmi)
        return float(val) if val else None

    @bmi.setter
    def bmi(self, value):
        self._bmi = encrypt_value(value)

    def save(self, *args, **kwargs):
        h = self.height
        w = self.weight
        
        if h is not None and h <= 0:
            raise ValidationError("Height must be greater than zero.")
        if w is not None and w <= 0:
            raise ValidationError("Weight must be greater than zero.")

        if h and w:
            # BMI = weight (kg) / [height (m)]^2

            height_m = h / 100
            calculated_bmi = round(w / (height_m ** 2), 2)
            self.bmi = calculated_bmi
            self.fitness_status = classify_bmi(calculated_bmi)
            profile = {
                'test_scores': self.fitness_test_scores or {},
                'recent_performances': list(
                    FitnessPerformance.objects.filter(student=self.student)
                    .order_by('-date')
                    .values('metric_name', 'score')[:10]
                ),
            }
            self.ai_recommendations = generate_recommendations(self.fitness_status, student_profile=profile)
        
        super().save(*args, **kwargs)
        
        # Save snapshot to history
        if h and w:
            HealthHistory.objects.create(
                student=self.student,
                height=h,
                weight=w,
                bmi=self.bmi,
                fitness_status=self.fitness_status
            )




    def __str__(self):
        return f"Health Record - {self.student.name}"

class FitnessPerformance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='performances', db_index=True)
    date = models.DateField(auto_now_add=True, db_index=True)
    metric_name = models.CharField(max_length=100, help_text="e.g., Endurance, Strength, Flexibility")
    score = models.FloatField()

    def __str__(self):
        return f"{self.metric_name} - {self.student.name} ({self.date})"

class HealthHistory(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='health_history', db_index=True)
    date = models.DateField(auto_now_add=True, db_index=True)

    height = models.FloatField()
    weight = models.FloatField()
    bmi = models.FloatField()
    fitness_status = models.CharField(max_length=50)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.name} - {self.date} (BMI: {self.bmi})"


class PESession(models.Model):
    """Physical Education Session for attendance tracking"""
    name = models.CharField(max_length=200, help_text="Session name or topic")
    date = models.DateField(db_index=True)
    section = models.CharField(max_length=50, db_index=True, help_text="Class/section for this session")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pe_sessions', limit_choices_to={'role': 'TEACHER'})
    description = models.TextField(blank=True, help_text="Session description or activities")
    start_time = models.TimeField(help_text="Session start time")
    end_time = models.TimeField(help_text="Session end time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']
        unique_together = ['date', 'section', 'start_time']
        indexes = [
            models.Index(fields=['date', 'section']),
            models.Index(fields=['teacher', 'date']),
        ]

    def __str__(self):
        return f"{self.name} - {self.section} ({self.date})"


class Attendance(models.Model):
    """Student attendance for PE sessions"""
    PRESENT = 'PRESENT'
    ABSENT = 'ABSENT'
    EXCUSED = 'EXCUSED'
    LATE = 'LATE'
    
    STATUS_CHOICES = [
        (PRESENT, 'Present'),
        (ABSENT, 'Absent'),
        (EXCUSED, 'Excused'),
        (LATE, 'Late'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    session = models.ForeignKey(PESession, on_delete=models.CASCADE, related_name='attendances')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PRESENT)
    notes = models.TextField(blank=True, help_text="Optional notes about attendance")
    marked_at = models.DateTimeField(auto_now_add=True)
    marked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='marked_attendances', limit_choices_to={'role': 'TEACHER'})

    class Meta:
        ordering = ['-marked_at']
        unique_together = ['student', 'session']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['student', 'marked_at']),
            models.Index(fields=['status', 'marked_at']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.status} ({self.session.date})"

