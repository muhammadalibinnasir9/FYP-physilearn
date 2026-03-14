from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.utils import timezone

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Enhanced user serializer with role information"""
    
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'role', 'role_display')
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name', 'role')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', 'USER')
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that includes user role and profile data"""
    
    @classmethod
    def get_token(cls, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        
        token = super().get_token(user)
        
        # Add custom claims
        token['user_id'] = user.id
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['full_name'] = f"{user.first_name} {user.last_name}".strip()
        
        # Determine user role
        if user.is_superuser:
            token['role'] = 'ADMIN'
        elif hasattr(user, 'role') and user.role == 'TEACHER':
            token['role'] = 'TEACHER'
            token['assigned_students_count'] = 0  # Placeholder
        elif hasattr(user, 'role') and user.role == 'PARENT':
            token['role'] = 'PARENT'
            token['children_count'] = 0  # Placeholder
        else:
            token['role'] = 'USER'
        
        # Add profile completion status
        profile_complete = bool(
            user.first_name and 
            user.last_name and 
            user.email and 
            token['role'] != 'USER'
        )
        token['profile_complete'] = profile_complete
        token['has_notification_preferences'] = False  # Placeholder
        
        return token
    
    def validate(self, attrs):
        """Enhanced validation with additional user data"""
        data = super().validate(attrs)
        
        # Add user profile data to response
        user = self.user
        
        refresh = self.get_token(user)
        access = refresh.access_token
        
        # Build response data
        response_data = {
            'refresh': str(refresh),
            'access': str(access),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': f"{user.first_name} {user.last_name}".strip(),
                'role': access.payload.get('role', 'USER'),
                'profile_complete': access.payload.get('profile_complete', False),
                'has_notification_preferences': access.payload.get('has_notification_preferences', False),
            }
        }
        
        # Add role-specific data
        role = access.payload.get('role', 'USER')
        if role == 'TEACHER':
            response_data['user']['assigned_students_count'] = 0
            response_data['user']['assigned_students'] = []
        
        elif role == 'PARENT':
            response_data['user']['children_count'] = 0
            response_data['user']['children'] = []
        
        elif role == 'ADMIN':
            # Add admin statistics
            response_data['user']['stats'] = {
                'total_users': User.objects.count(),
                'total_students': 0,
                'total_teachers': User.objects.filter(role='TEACHER').count(),
                'total_parents': User.objects.filter(role='PARENT').count(),
            }
        
        return response_data

class LogoutSerializer(serializers.Serializer):
    """Serializer for logout functionality"""
    
    refresh_token = serializers.CharField(required=False)
    
    def validate(self, attrs):
        """Validate refresh token for logout"""
        refresh_token = attrs.get('refresh_token')
        
        if not refresh_token:
            # Try to get from cookie
            refresh_token = self.context.get('request').COOKIES.get('refresh_token')
        
        if not refresh_token:
            raise serializers.ValidationError(
                "Refresh token is required for logout"
            )
        
        return attrs
from .models import Student, HealthRecord, HealthHistory, FitnessPerformance, AcademicTerm, FitnessTestParameter, PESession, Attendance

class HealthHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthHistory
        fields = ('date', 'height', 'weight', 'bmi', 'fitness_status')

class FitnessPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitnessPerformance
        fields = ('id', 'student', 'date', 'metric_name', 'score')


class HealthRecordSerializer(serializers.ModelSerializer):
    height = serializers.FloatField()
    weight = serializers.FloatField()
    bmi = serializers.FloatField(read_only=True)

    class Meta:
        model = HealthRecord
        fields = ('id', 'student', 'height', 'weight', 'bmi', 'fitness_status', 'ai_recommendations', 'activity_record', 'fitness_test_scores')
        extra_kwargs = {
            'activity_record': {'required': False},
            'fitness_test_scores': {'required': False},
            'fitness_status': {'required': False},
            'ai_recommendations': {'required': False},
        }


class StudentSerializer(serializers.ModelSerializer):
    health_record = HealthRecordSerializer(read_only=True)
    health_history = HealthHistorySerializer(many=True, read_only=True)
    performances = FitnessPerformanceSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ('id', 'name', 'roll_number', 'section', 'parent', 'teacher', 'health_record', 'health_history', 'performances')


class StudentAdminSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    parent_name = serializers.CharField(source='parent.get_full_name', read_only=True)

    class Meta:
        model = Student
        fields = ('id', 'name', 'roll_number', 'section', 'parent', 'parent_name', 'teacher', 'teacher_name', 'is_active')


class AcademicTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = ('id', 'name', 'start_date', 'end_date', 'is_active')


class FitnessTestParameterSerializer(serializers.ModelSerializer):
    term_name = serializers.CharField(source='term.name', read_only=True)

    class Meta:
        model = FitnessTestParameter
        fields = ('id', 'term', 'term_name', 'metric_name', 'passing_score', 'max_score')


class PESessionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    attendance_count = serializers.SerializerMethodField()
    present_count = serializers.SerializerMethodField()
    absent_count = serializers.SerializerMethodField()

    class Meta:
        model = PESession
        fields = (
            'id', 'name', 'date', 'section', 'teacher', 'teacher_name',
            'description', 'start_time', 'end_time', 'created_at', 'updated_at',
            'attendance_count', 'present_count', 'absent_count'
        )
        read_only_fields = ('teacher', 'created_at', 'updated_at')

    def get_attendance_count(self, obj):
        return obj.attendances.count()

    def get_present_count(self, obj):
        return obj.attendances.filter(status='PRESENT').count()

    def get_absent_count(self, obj):
        return obj.attendances.filter(status='ABSENT').count()


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_roll_number = serializers.CharField(source='student.roll_number', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    marked_by_name = serializers.CharField(source='marked_by.get_full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = (
            'id', 'student', 'student_name', 'student_roll_number',
            'session', 'session_name', 'status', 'notes', 'marked_at', 'marked_by_name'
        )
        read_only_fields = ('marked_at', 'marked_by')


class AttendanceBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk attendance creation"""
    attendances = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        help_text="List of attendance records with student_id and status"
    )

    def validate_attendances(self, value):
        """Validate attendance data format"""
        required_fields = ['student_id', 'status']
        valid_statuses = [choice[0] for choice in Attendance.STATUS_CHOICES]
        
        for i, attendance in enumerate(value):
            for field in required_fields:
                if field not in attendance:
                    raise serializers.ValidationError(
                        f"Attendance record {i+1} missing required field: {field}"
                    )
            
            if attendance['status'] not in valid_statuses:
                raise serializers.ValidationError(
                    f"Attendance record {i+1} has invalid status: {attendance['status']}"
                )
        
        return value


class AttendanceAnalyticsSerializer(serializers.Serializer):
    """Serializer for attendance analytics data"""
    date = serializers.DateField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    excused_count = serializers.IntegerField()
    late_count = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    section = serializers.CharField()


