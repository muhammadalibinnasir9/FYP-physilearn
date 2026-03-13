from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics, viewsets, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.http import HttpResponse
from .models import Student, HealthRecord, FitnessPerformance, AcademicTerm, FitnessTestParameter, TeacherSection, PESession, Attendance
from .permissions import IsAdmin, IsTeacher, IsParent
from .reports import generate_student_pdf
from django.db.models import Avg, Count, Q
from django.db import transaction
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from .serializers import (
    RegisterSerializer, UserSerializer, 
    CustomTokenObtainPairSerializer, LogoutSerializer,
    HealthRecordSerializer, FitnessPerformanceSerializer,
    AcademicTermSerializer, FitnessTestParameterSerializer,
    StudentAdminSerializer, PESessionSerializer, AttendanceSerializer,
    AttendanceBulkCreateSerializer, AttendanceAnalyticsSerializer
)
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils import timezone

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_view(request):
    """Get current user profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def heartbeat(request):
    """
    Simple API endpoint to check if the backend is running.
    """
    return Response({"status": "healthy", "message": "PhysiLearn Backend is running!"}, status=status.HTTP_200_OK)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    """Logout view to invalidate refresh token"""
    serializer = LogoutSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    try:
        # In a real implementation, you would blacklist the token here
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        return UserSerializer


class AcademicTermViewSet(viewsets.ModelViewSet):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.is_active:
            AcademicTerm.objects.exclude(id=instance.id).update(is_active=False)

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.is_active:
            AcademicTerm.objects.exclude(id=instance.id).update(is_active=False)


class FitnessTestParameterViewSet(viewsets.ModelViewSet):
    queryset = FitnessTestParameter.objects.select_related('term').all()
    serializer_class = FitnessTestParameterSerializer
    permission_classes = [IsAdmin]


class StudentAdminViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.select_related('parent', 'teacher').all()
    serializer_class = StudentAdminSerializer
    permission_classes = [IsAdmin]


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_teacher_and_assign_sections_view(request):
    username = (request.data.get('username') or '').strip()
    email = (request.data.get('email') or '').strip()
    password = request.data.get('password') or ''
    first_name = (request.data.get('first_name') or '').strip()
    last_name = (request.data.get('last_name') or '').strip()

    raw_sections = request.data.get('sections') or []
    if isinstance(raw_sections, str):
        sections = [s.strip() for s in raw_sections.split(',') if s.strip()]
    elif isinstance(raw_sections, list):
        sections = [str(s).strip() for s in raw_sections if str(s).strip()]
    else:
        sections = []

    if not username:
        return Response({'username': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not email:
        return Response({'email': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not password:
        return Response({'password': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not first_name:
        return Response({'first_name': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not last_name:
        return Response({'last_name': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not sections:
        return Response({'sections': ['At least one section is required (e.g., 7-A).']}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        teacher = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='TEACHER',
        )

        # Create explicit TeacherSection records
        teacher_sections = []
        for section in sections:
            teacher_sections.append(
                TeacherSection(
                    teacher=teacher,
                    section=section,
                    assigned_by=request.user
                )
            )
        TeacherSection.objects.bulk_create(teacher_sections, ignore_conflicts=True)

        # Also update existing students in those sections
        updated = Student.objects.filter(section__in=sections).update(teacher=teacher)

    return Response(
        {
            'teacher': UserSerializer(teacher).data,
            'sections': sections,
            'students_assigned': updated,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_parent_and_link_students_view(request):
    username = (request.data.get('username') or '').strip()
    email = (request.data.get('email') or '').strip()
    password = request.data.get('password') or ''
    first_name = (request.data.get('first_name') or '').strip()
    last_name = (request.data.get('last_name') or '').strip()

    raw_student_ids = request.data.get('student_ids') or []
    if isinstance(raw_student_ids, str):
        student_ids = [s.strip() for s in raw_student_ids.split(',') if s.strip()]
    elif isinstance(raw_student_ids, list):
        student_ids = [str(s).strip() for s in raw_student_ids if str(s).strip()]
    else:
        student_ids = []

    try:
        student_ids_int = [int(x) for x in student_ids]
    except ValueError:
        return Response({'student_ids': ['Student IDs must be integers.']}, status=status.HTTP_400_BAD_REQUEST)

    if not username:
        return Response({'username': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not email:
        return Response({'email': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not password:
        return Response({'password': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not first_name:
        return Response({'first_name': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not last_name:
        return Response({'last_name': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not student_ids_int:
        return Response({'student_ids': ['At least one Student ID is required.']}, status=status.HTTP_400_BAD_REQUEST)

    existing_count = Student.objects.filter(id__in=student_ids_int).count()
    if existing_count != len(set(student_ids_int)):
        return Response({'student_ids': ['One or more Student IDs do not exist.']}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        parent = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role='PARENT',
        )

        updated = Student.objects.filter(id__in=student_ids_int).update(parent=parent)

    return Response(
        {
            'parent': UserSerializer(parent).data,
            'student_ids': student_ids_int,
            'students_linked': updated,
        },
        status=status.HTTP_201_CREATED,
    )


class IsAdminOrTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return IsAdmin().has_permission(request, view) or IsTeacher().has_permission(request, view)


class HealthRecordViewSet(viewsets.ModelViewSet):
    queryset = HealthRecord.objects.select_related('student', 'student__teacher', 'student__parent')
    serializer_class = HealthRecordSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def _can_access_student(self, user, student: Student) -> bool:
        if getattr(user, 'role', None) == 'ADMIN':
            return True
        if getattr(user, 'role', None) == 'TEACHER':
            # Check if teacher is assigned to the student's section
            return TeacherSection.objects.filter(
                teacher=user,
                section=student.section
            ).exists()
        if getattr(user, 'role', None) == 'PARENT':
            # Parent can only access their own children
            return student.parent == user
        return False

    def create(self, request, *args, **kwargs):
        student_id = request.data.get('student')
        if not student_id:
            return Response({'student': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.select_related('teacher', 'parent').get(id=student_id)
        except Student.DoesNotExist:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not self._can_access_student(request.user, student):
            return Response({'detail': 'You do not have permission to update this student.'}, status=status.HTTP_403_FORBIDDEN)

        instance, _ = HealthRecord.objects.get_or_create(student=student)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_access_student(request.user, instance.student):
            return Response({'detail': 'You do not have permission to update this student.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._can_access_student(request.user, instance.student):
            return Response({'detail': 'You do not have permission to update this student.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)


class FitnessPerformanceViewSet(viewsets.ModelViewSet):
    queryset = FitnessPerformance.objects.select_related('student', 'student__teacher', 'student__parent')
    serializer_class = FitnessPerformanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def _can_access_student(self, user, student: Student) -> bool:
        if getattr(user, 'role', None) == 'ADMIN':
            return True
        if getattr(user, 'role', None) == 'TEACHER':
            # Check if teacher is assigned to the student's section
            return TeacherSection.objects.filter(
                teacher=user,
                section=student.section
            ).exists()
        if getattr(user, 'role', None) == 'PARENT':
            # Parent can only access their own children
            return student.parent == user
        return False

    def create(self, request, *args, **kwargs):
        student_id = request.data.get('student')
        if not student_id:
            return Response({'student': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.select_related('teacher', 'parent').get(id=student_id)
        except Student.DoesNotExist:
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not self._can_access_student(request.user, student):
            return Response({'detail': 'You do not have permission to update this student.'}, status=status.HTTP_403_FORBIDDEN)

        return super().create(request, *args, **kwargs)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_sections_view(request):
    """Get sections assigned to the current teacher"""
    if getattr(request.user, 'role', None) != 'TEACHER':
        return Response(
            {'detail': 'Only teachers can access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    # Get assigned sections
    assigned_sections = TeacherSection.objects.filter(
        teacher=request.user
    ).select_related('assigned_by').order_by('section')
    
    sections_data = []
    for ts in assigned_sections:
        sections_data.append({
            'section': ts.section,
            'assigned_at': ts.assigned_at.isoformat(),
            'assigned_by': f"{ts.assigned_by.first_name} {ts.assigned_by.last_name}".strip() if ts.assigned_by else None,
        })
    
    return Response({
        'teacher_id': request.user.id,
        'teacher_name': f"{request.user.first_name} {request.user.last_name}".strip(),
        'sections': sections_data,
        'total_sections': len(sections_data),
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def students_list_view(request):
    """Get all students - filtered by role and assignments"""
    role = getattr(request.user, 'role', None)
    
    # Handle teacher_id parameter for backward compatibility
    teacher_id_param = request.GET.get('teacher_id')
    
    students = Student.objects.select_related('parent', 'teacher')

    if role == 'ADMIN':
        students = students.all()
        
        # If admin specifies teacher_id=me, treat as current user (though admin can see all)
        if teacher_id_param == 'me':
            # Admin requesting their own assigned sections (if they were a teacher)
            assigned_sections = TeacherSection.objects.filter(
                teacher=request.user
            ).values_list('section', flat=True)
            
            if assigned_sections:
                students = students.filter(section__in=assigned_sections, is_active=True)
            else:
                students = students.none()
                
    elif role == 'TEACHER':
        # Check if teacher_id parameter is provided
        if teacher_id_param:
            if teacher_id_param == 'me':
                # Filter by current teacher's assigned sections
                assigned_sections = TeacherSection.objects.filter(
                    teacher=request.user
                ).values_list('section', flat=True)
                
                # If teacher has no assigned sections, return empty list
                if not assigned_sections:
                    return Response([], status=status.HTTP_200_OK)
                
                # Filter students by assigned sections AND is_active
                students = students.filter(
                    section__in=assigned_sections,
                    is_active=True
                )
            else:
                # Teacher trying to access another teacher's students - not allowed
                return Response(
                    {'detail': 'Teachers can only view their own assigned students. Use teacher_id=me to view your students.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            # Default behavior: filter by current teacher's assigned sections
            assigned_sections = TeacherSection.objects.filter(
                teacher=request.user
            ).values_list('section', flat=True)
            
            # If teacher has no assigned sections, return empty list
            if not assigned_sections:
                return Response([], status=status.HTTP_200_OK)
            
            # Filter students by assigned sections AND is_active
            students = students.filter(
                section__in=assigned_sections,
                is_active=True
            )
    elif role == 'PARENT':
        students = students.filter(parent_id=request.user.id, is_active=True)
    else:
        return Response(
            {'detail': 'You do not have permission to view students.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    students_data = []
    for student in students:
        students_data.append({
            'id': student.id,
            'name': student.name,
            'roll_number': student.roll_number,
            'section': student.section,
            'parent': student.parent.id if student.parent else None,
            'parent_name': f"{student.parent.first_name} {student.parent.last_name}".strip() if student.parent else None,
            'parent_id': student.parent.id if student.parent else None,
            'teacher': student.teacher.id if student.teacher else None,
            'teacher_name': f"{student.teacher.first_name} {student.teacher.last_name}".strip() if student.teacher else None,
            'teacher_id': student.teacher.id if student.teacher else None,
        })
    
    return Response(students_data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsParent])
def my_children_view(request):
    """Get only the children linked to the authenticated parent"""
    try:
        # Get all students linked to this parent
        children = Student.objects.filter(
            parent_id=request.user.id, 
            is_active=True
        ).select_related('teacher').order_by('name')
        
        children_data = []
        for child in children:
            children_data.append({
                'id': child.id,
                'name': child.name,
                'roll_number': child.roll_number,
                'section': child.section,
                'teacher': child.teacher.id if child.teacher else None,
                'teacher_name': f"{child.teacher.first_name} {child.teacher.last_name}".strip() if child.teacher else None,
                'teacher_id': child.teacher.id if child.teacher else None,
                'is_active': child.is_active,
            })
        
        return Response({
            'children': children_data,
            'count': len(children_data),
            'parent': {
                'id': request.user.id,
                'name': f"{request.user.first_name} {request.user.last_name}".strip(),
                'email': request.user.email,
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'detail': f'Error retrieving children: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_analytics_view(request):
    """Comprehensive analytics endpoint for admin dashboard"""
    try:
        # BMI Distribution Analysis
        bmi_data = calculate_bmi_distribution()
        
        # BMI Distribution by Grade/Section
        bmi_by_grade = calculate_bmi_distribution_by_grade()
        
        # At-risk students (Obese/Underweight)
        at_risk_students = get_at_risk_students()
        
        # Activity Trends (last 6 months)
        activity_trends = calculate_activity_trends()
        
        # Performance Metrics
        performance_metrics = calculate_performance_metrics()
        
        return Response({
            'bmi_distribution': bmi_data,
            'bmi_by_grade': bmi_by_grade,
            'at_risk_students': at_risk_students,
            'activity_trends': activity_trends,
            'performance_metrics': performance_metrics,
            'last_updated': timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Error fetching analytics data: {str(e)}',
            'bmi_distribution': {'categories': {'underweight': 0, 'normal': 0, 'overweight': 0, 'obese': 0}, 'total_students': 0},
            'bmi_by_grade': [],
            'at_risk_students': [],
            'activity_trends': {'months': [], 'participation_rates': [], 'average_participation': 0},
            'performance_metrics': {'grade_performance': [], 'total_sections': 0, 'overall_average_score': 0},
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def calculate_bmi_distribution():
    """Calculate BMI distribution from student health records"""
    try:
        # Get all health records with valid height and weight
        health_records = HealthRecord.objects.filter(
            _height__isnull=False,
            _weight__isnull=False
        ).select_related('student')
        
        bmi_categories = {
            'underweight': 0,
            'normal': 0,
            'overweight': 0,
            'obese': 0
        }
        
        total_students = 0
        
        for record in health_records:
            try:
                # Decrypt height and weight
                height = float(record.height) / 100  # Convert cm to meters
                weight = float(record.weight)
                
                # Calculate BMI
                bmi = weight / (height * height)
                
                # Categorize BMI
                if bmi < 18.5:
                    bmi_categories['underweight'] += 1
                elif 18.5 <= bmi < 25:
                    bmi_categories['normal'] += 1
                elif 25 <= bmi < 30:
                    bmi_categories['overweight'] += 1
                else:
                    bmi_categories['obese'] += 1
                    
                total_students += 1
                
            except (ValueError, TypeError, ZeroDivisionError):
                # Skip records with invalid data
                continue
        
        # Calculate percentages
        if total_students > 0:
            for category in bmi_categories:
                bmi_categories[category] = round(
                    (bmi_categories[category] / total_students) * 100, 2
                )
        
        return {
            'categories': bmi_categories,
            'total_students': total_students
        }
        
    except Exception as e:
        print(f"Error calculating BMI distribution: {e}")
        return {
            'categories': {'underweight': 0, 'normal': 0, 'overweight': 0, 'obese': 0},
            'total_students': 0
        }


def calculate_activity_trends():
    """Calculate activity trends over last 6 months"""
    try:
        # Get date range for last 6 months
        end_date = timezone.now()
        start_date = end_date - timedelta(days=180)  # 6 months
        
        # For now, return mock data since activity tracking isn't fully implemented
        # In a real implementation, this would query activity logs
        months = []
        participation_rates = []
        
        for i in range(6):
            month_date = start_date + timedelta(days=i*30)
            months.append(month_date.strftime('%b %Y'))
            # Mock participation rates (replace with real data)
            participation_rates.append(65 + (i * 5) % 30)
        
        return {
            'months': months,
            'participation_rates': participation_rates,
            'average_participation': round(sum(participation_rates) / len(participation_rates), 2)
        }
        
    except Exception as e:
        print(f"Error calculating activity trends: {e}")
        return {
            'months': [],
            'participation_rates': [],
            'average_participation': 0
        }


def calculate_performance_metrics():
    """Calculate performance metrics by grade/section"""
    try:
        # Get students grouped by section
        students_by_section = Student.objects.values('section').annotate(
            student_count=Count('id')
        ).order_by('section')
        
        grade_performance = []
        
        for section_data in students_by_section:
            section = section_data['section'] or 'Unassigned'
            student_count = section_data['student_count']
            
            # Mock performance data (replace with real fitness test scores)
            avg_score = 75 + (hash(section) % 20)  # Pseudo-random but consistent
            
            grade_performance.append({
                'section': section,
                'student_count': student_count,
                'average_score': round(avg_score, 2),
                'participation_rate': round(80 + (hash(section) % 15), 2)
            })
        
        return {
            'grade_performance': grade_performance,
            'total_sections': len(grade_performance),
            'overall_average_score': round(
                sum(g['average_score'] for g in grade_performance) / len(grade_performance) if grade_performance else 0, 2
            )
        }
        
    except Exception as e:
        print(f"Error calculating performance metrics: {e}")
        return {
            'grade_performance': [],
            'total_sections': 0,
            'overall_average_score': 0
        }


def calculate_bmi_distribution_by_grade():
    """Calculate BMI distribution broken down by grade/section"""
    try:
        # Get all sections
        sections = Student.objects.values_list('section', flat=True).distinct().order_by('section')
        
        bmi_by_grade = []
        
        for section in sections:
            if not section:
                continue
                
            # Get health records for students in this section
            health_records = HealthRecord.objects.filter(
                student__section=section,
                _height__isnull=False,
                _weight__isnull=False
            ).select_related('student')
            
            categories = {
                'underweight': 0,
                'normal': 0,
                'overweight': 0,
                'obese': 0
            }
            total = 0
            
            for record in health_records:
                try:
                    height = float(record.height) / 100
                    weight = float(record.weight)
                    bmi = weight / (height * height)
                    
                    if bmi < 18.5:
                        categories['underweight'] += 1
                    elif 18.5 <= bmi < 25:
                        categories['normal'] += 1
                    elif 25 <= bmi < 30:
                        categories['overweight'] += 1
                    else:
                        categories['obese'] += 1
                    
                    total += 1
                except (ValueError, TypeError, ZeroDivisionError):
                    continue
            
            if total > 0:
                # Calculate percentages
                for cat in categories:
                    categories[cat] = round((categories[cat] / total) * 100, 2)
                
                bmi_by_grade.append({
                    'section': section,
                    'total_students': total,
                    'underweight': categories['underweight'],
                    'normal': categories['normal'],
                    'overweight': categories['overweight'],
                    'obese': categories['obese'],
                    'at_risk_count': categories['underweight'] + categories['obese']
                })
        
        return bmi_by_grade
        
    except Exception as e:
        print(f"Error calculating BMI by grade: {e}")
        return []


def get_at_risk_students():
    """Get list of students who are Obese or Underweight (at-risk)"""
    try:
        health_records = HealthRecord.objects.filter(
            _height__isnull=False,
            _weight__isnull=False
        ).select_related('student', 'student__teacher')
        
        at_risk = []
        
        for record in health_records:
            try:
                height = float(record.height) / 100
                weight = float(record.weight)
                bmi = weight / (height * height)
                
                # Only include at-risk students (Obese or Underweight)
                if bmi < 18.5 or bmi >= 30:
                    student = record.student
                    
                    if bmi < 18.5:
                        category = 'Underweight'
                        risk_level = 'medium'
                    else:
                        category = 'Obese'
                        risk_level = 'high'
                    
                    at_risk.append({
                        'id': student.id,
                        'name': student.name,
                        'roll_number': student.roll_number,
                        'section': student.section,
                        'bmi': round(bmi, 2),
                        'category': category,
                        'risk_level': risk_level,
                        'teacher_name': f"{student.teacher.first_name} {student.teacher.last_name}".strip() if student.teacher else None,
                    })
                    
            except (ValueError, TypeError, ZeroDivisionError):
                continue
        
        # Sort by BMI - underweight first (ascending), then obese (descending)
        at_risk.sort(key=lambda x: x['bmi'])
        
        return at_risk
        
    except Exception as e:
        print(f"Error getting at-risk students: {e}")
        return []


@api_view(['GET'])
@permission_classes([AllowAny])
def class_summary_view(request):
    """Simplified class summary view without student dependencies"""
    return Response({
        "average_bmi": 0,
        "participation_rate": 0,
        "total_students": 0,
        "records_collected": 0,
        "message": "Student model not yet implemented"
    })


# ─────────────────────────────────────────────────────────────────────────────
# Attendance Management ViewSets
# ─────────────────────────────────────────────────────────────────────────────

class PESessionViewSet(viewsets.ModelViewSet):
    """ViewSet for PE Session management"""
    serializer_class = PESessionSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        """Filter sessions by current teacher's assigned sections"""
        user = self.request.user
        if getattr(user, 'role', None) != 'TEACHER':
            return PESession.objects.none()
        
        # Get sections assigned to this teacher
        assigned_sections = TeacherSection.objects.filter(
            teacher=user
        ).values_list('section', flat=True)
        
        return PESession.objects.filter(
            section__in=assigned_sections,
            teacher=user
        ).select_related('teacher').prefetch_related('attendances')

    def perform_create(self, serializer):
        """Set teacher to current user on creation"""
        serializer.save(teacher=self.request.user)

    def _can_access_session(self, session):
        """Check if teacher can access this session"""
        user = self.request.user
        if getattr(user, 'role', None) != 'TEACHER':
            return False
        
        # Check if session belongs to teacher's assigned section
        return TeacherSection.objects.filter(
            teacher=user,
            section=session.section
        ).exists()

    def retrieve(self, request, *args, **kwargs):
        """Get session details with attendance"""
        instance = self.get_object()
        if not self._can_access_session(instance):
            return Response(
                {'detail': 'You do not have permission to access this session.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Update session details"""
        instance = self.get_object()
        if not self._can_access_session(instance):
            return Response(
                {'detail': 'You do not have permission to update this session.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete session"""
        instance = self.get_object()
        if not self._can_access_session(instance):
            return Response(
                {'detail': 'You do not have permission to delete this session.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


class AttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for attendance management"""
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        """Filter attendance by current teacher's sessions"""
        user = self.request.user
        if getattr(user, 'role', None) != 'TEACHER':
            return Attendance.objects.none()
        
        # Get sessions created by this teacher
        teacher_sessions = PESession.objects.filter(teacher=user)
        
        return Attendance.objects.filter(
            session__in=teacher_sessions
        ).select_related('student', 'session', 'marked_by')

    def _can_access_attendance(self, attendance):
        """Check if teacher can access this attendance record"""
        user = self.request.user
        if getattr(user, 'role', None) != 'TEACHER':
            return False
        
        # Check if session belongs to teacher
        return attendance.session.teacher == user

    def create(self, request, *args, **kwargs):
        """Create attendance record"""
        student_id = request.data.get('student')
        session_id = request.data.get('session')
        
        if not student_id or not session_id:
            return Response(
                {'detail': 'Student and session are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(id=student_id)
            session = PESession.objects.get(id=session_id)
        except (Student.DoesNotExist, PESession.DoesNotExist):
            return Response(
                {'detail': 'Student or session not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permissions
        if session.teacher != request.user:
            return Response(
                {'detail': 'You can only mark attendance for your own sessions.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if student belongs to session's section
        if student.section != session.section:
            return Response(
                {'detail': 'Student does not belong to this session section.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if attendance already exists
        if Attendance.objects.filter(student=student, session=session).exists():
            return Response(
                {'detail': 'Attendance already recorded for this student.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create attendance
        attendance = Attendance.objects.create(
            student=student,
            session=session,
            status=request.data.get('status', 'PRESENT'),
            notes=request.data.get('notes', ''),
            marked_by=request.user
        )

        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update attendance record"""
        instance = self.get_object()
        if not self._can_access_attendance(instance):
            return Response(
                {'detail': 'You do not have permission to update this attendance.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete attendance record"""
        instance = self.get_object()
        if not self._can_access_attendance(instance):
            return Response(
                {'detail': 'You do not have permission to delete this attendance.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTeacher])
def bulk_attendance_view(request):
    """Bulk create attendance for a session"""
    session_id = request.data.get('session_id')
    attendances_data = request.data.get('attendances', [])

    if not session_id:
        return Response(
            {'detail': 'Session ID is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        session = PESession.objects.get(id=session_id)
    except PESession.DoesNotExist:
        return Response(
            {'detail': 'Session not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    if session.teacher != request.user:
        return Response(
            {'detail': 'You can only mark attendance for your own sessions.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Validate attendance data
    serializer = AttendanceBulkCreateSerializer(data={'attendances': attendances_data})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    created_attendances = []
    errors = []

    with transaction.atomic():
        for attendance_data in attendances_data:
            student_id = attendance_data.get('student_id')
            status = attendance_data.get('status')
            notes = attendance_data.get('notes', '')

            try:
                student = Student.objects.get(id=student_id)

                # Check if student belongs to session's section
                if student.section != session.section:
                    errors.append({
                        'student_id': student_id,
                        'error': 'Student does not belong to this session section'
                    })
                    continue

                # Check if attendance already exists
                if Attendance.objects.filter(student=student, session=session).exists():
                    errors.append({
                        'student_id': student_id,
                        'error': 'Attendance already recorded'
                    })
                    continue

                # Create attendance
                attendance = Attendance.objects.create(
                    student=student,
                    session=session,
                    status=status,
                    notes=notes,
                    marked_by=request.user
                )

                created_attendances.append(attendance)

            except Student.DoesNotExist:
                errors.append({
                    'student_id': student_id,
                    'error': 'Student not found'
                })

    response_data = {
        'created': len(created_attendances),
        'errors': len(errors),
        'attendances': AttendanceSerializer(created_attendances, many=True).data,
        'error_details': errors
    }

    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsTeacher])
def attendance_analytics_view(request):
    """Get attendance analytics for teacher's sessions"""
    user = request.user
    if getattr(user, 'role', None) != 'TEACHER':
        return Response(
            {'detail': 'Only teachers can access attendance analytics.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get date range from query params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    section = request.GET.get('section')

    # Get teacher's sessions
    queryset = PESession.objects.filter(teacher=user)
    
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    if section:
        queryset = queryset.filter(section=section)

    sessions = queryset.prefetch_related('attendances')

    analytics_data = []
    
    for session in sessions:
        attendances = session.attendances.all()
        total_students = attendances.count()
        
        if total_students == 0:
            continue
            
        present_count = attendances.filter(status='PRESENT').count()
        absent_count = attendances.filter(status='ABSENT').count()
        excused_count = attendances.filter(status='EXCUSED').count()
        late_count = attendances.filter(status='LATE').count()
        
        attendance_rate = (present_count / total_students) * 100 if total_students > 0 else 0

        analytics_data.append({
            'date': session.date,
            'session_name': session.name,
            'section': session.section,
            'total_students': total_students,
            'present_count': present_count,
            'absent_count': absent_count,
            'excused_count': excused_count,
            'late_count': late_count,
            'attendance_rate': round(attendance_rate, 2)
        })

    return Response({
        'analytics': analytics_data,
        'summary': {
            'total_sessions': len(analytics_data),
            'average_attendance_rate': round(
                sum(item['attendance_rate'] for item in analytics_data) / len(analytics_data) if analytics_data else 0, 2
            )
        }
    }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# Student Historical Data Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_health_history_view(request, student_id):
    """Get student's health history (BMI records over time)"""
    user = request.user
    
    # Check permissions
    if getattr(user, 'role', None) == 'TEACHER':
        # Teachers can only access students in their assigned sections
        assigned_sections = TeacherSection.objects.filter(
            teacher=user
        ).values_list('section', flat=True)
        
        try:
            student = Student.objects.get(id=student_id, section__in=assigned_sections)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not in your assigned sections.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'PARENT':
        # Parents can only access their own children
        try:
            student = Student.objects.get(id=student_id, parent=user)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not your child.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'ADMIN':
        # Admins can access any student
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {'detail': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get health history
    health_history = HealthHistory.objects.filter(
        student=student
    ).order_by('date')
    
    # Get current health record
    try:
        current_health_record = HealthRecord.objects.get(student=student)
    except HealthRecord.DoesNotExist:
        current_health_record = None
    
    # Build response data
    history_data = []
    for record in health_history:
        history_data.append({
            'date': record.date,
            'height': record.height,
            'weight': record.weight,
            'bmi': record.bmi,
            'fitness_status': record.fitness_status,
        })
    
    # Add current record if not in history
    if current_health_record:
        current_data = {
            'date': current_health_record.updated_at.date(),
            'height': current_health_record.height,
            'weight': current_health_record.weight,
            'bmi': current_health_record.bmi,
            'fitness_status': current_health_record.fitness_status,
            'is_current': True,
            'ai_recommendations': current_health_record.ai_recommendations,
        }
        
        # Check if current record already exists in history
        if not any(h['date'] == current_data['date'] for h in history_data):
            history_data.append(current_data)
    
    # Sort by date
    history_data.sort(key=lambda x: x['date'])
    
    # Calculate BMI trends
    if len(history_data) > 1:
        bmi_values = [record['bmi'] for record in history_data if record['bmi']]
        if bmi_values:
            bmi_trend = bmi_values[-1] - bmi_values[0]
            bmi_change_percentage = (bmi_trend / bmi_values[0]) * 100 if bmi_values[0] != 0 else 0
        else:
            bmi_trend = 0
            bmi_change_percentage = 0
    else:
        bmi_trend = 0
        bmi_change_percentage = 0
    
    response_data = {
        'student_id': student.id,
        'student_name': student.name,
        'section': student.section,
        'health_history': history_data,
        'total_records': len(history_data),
        'bmi_trend': round(bmi_trend, 2),
        'bmi_change_percentage': round(bmi_change_percentage, 2),
        'current_bmi': current_health_record.bmi if current_health_record else None,
        'current_fitness_status': current_health_record.fitness_status if current_health_record else None,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_fitness_progress_view(request, student_id):
    """Get student's fitness test progress over time"""
    user = request.user
    
    # Check permissions (same as health history)
    if getattr(user, 'role', None) == 'TEACHER':
        assigned_sections = TeacherSection.objects.filter(
            teacher=user
        ).values_list('section', flat=True)
        
        try:
            student = Student.objects.get(id=student_id, section__in=assigned_sections)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not in your assigned sections.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'PARENT':
        try:
            student = Student.objects.get(id=student_id, parent=user)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not your child.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'ADMIN':
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {'detail': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get fitness performances
    performances = FitnessPerformance.objects.filter(
        student=student
    ).order_by('date', 'metric_name')
    
    # Group by metric name
    metrics_data = {}
    for performance in performances:
        metric_name = performance.metric_name
        if metric_name not in metrics_data:
            metrics_data[metric_name] = []
        
        metrics_data[metric_name].append({
            'date': performance.date,
            'score': performance.score,
        })
    
    # Calculate progress for each metric
    progress_summary = []
    for metric_name, records in metrics_data.items():
        if len(records) > 1:
            first_score = records[0]['score']
            last_score = records[-1]['score']
            score_change = last_score - first_score
            score_change_percentage = (score_change / first_score) * 100 if first_score != 0 else 0
            
            # Determine trend
            if score_change > 0:
                trend = 'improving'
            elif score_change < 0:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            score_change = 0
            score_change_percentage = 0
            trend = 'insufficient_data'
        
        progress_summary.append({
            'metric_name': metric_name,
            'total_tests': len(records),
            'latest_score': records[-1]['score'] if records else None,
            'first_score': records[0]['score'] if records else None,
            'score_change': round(score_change, 2),
            'score_change_percentage': round(score_change_percentage, 2),
            'trend': trend,
            'records': records,
        })
    
    # Sort by latest score (highest first)
    progress_summary.sort(key=lambda x: x['latest_score'] or 0, reverse=True)
    
    response_data = {
        'student_id': student.id,
        'student_name': student.name,
        'section': student.section,
        'fitness_progress': progress_summary,
        'total_metrics': len(metrics_data),
        'total_tests': len(performances),
        'latest_test_date': performances.last().date if performances.exists() else None,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_attendance_trends_view(request, student_id):
    """Get student's attendance trends over time"""
    user = request.user
    
    # Check permissions (same as health history)
    if getattr(user, 'role', None) == 'TEACHER':
        assigned_sections = TeacherSection.objects.filter(
            teacher=user
        ).values_list('section', flat=True)
        
        try:
            student = Student.objects.get(id=student_id, section__in=assigned_sections)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not in your assigned sections.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'PARENT':
        try:
            student = Student.objects.get(id=student_id, parent=user)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not your child.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'ADMIN':
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {'detail': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get attendance records
    attendances = Attendance.objects.filter(
        student=student
    ).select_related('session').order_by('session__date')
    
    # Group by month for trends
    monthly_attendance = {}
    status_counts = {'PRESENT': 0, 'ABSENT': 0, 'EXCUSED': 0, 'LATE': 0}
    
    for attendance in attendances:
        month_key = attendance.session.date.strftime('%Y-%m')
        if month_key not in monthly_attendance:
            monthly_attendance[month_key] = {
                'month': month_key,
                'total_sessions': 0,
                'present': 0,
                'absent': 0,
                'excused': 0,
                'late': 0,
                'attendance_rate': 0,
            }
        
        monthly_attendance[month_key]['total_sessions'] += 1
        monthly_attendance[month_key][attendance.status.lower()] += 1
        status_counts[attendance.status] += 1
    
    # Calculate monthly attendance rates
    for month_data in monthly_attendance.values():
        if month_data['total_sessions'] > 0:
            month_data['attendance_rate'] = round(
                (month_data['present'] / month_data['total_sessions']) * 100, 2
            )
    
    # Convert to sorted list
    monthly_trends = sorted(monthly_attendance.values(), key=lambda x: x['month'])
    
    # Calculate overall statistics
    total_sessions = attendances.count()
    overall_attendance_rate = 0
    if total_sessions > 0:
        overall_attendance_rate = round((status_counts['PRESENT'] / total_sessions) * 100, 2)
    
    # Calculate trend (last 3 months vs previous 3 months)
    if len(monthly_trends) >= 6:
        recent_months = monthly_trends[-3:]
        previous_months = monthly_trends[-6:-3]
        
        recent_rate = sum(m['attendance_rate'] for m in recent_months) / len(recent_months)
        previous_rate = sum(m['attendance_rate'] for m in previous_months) / len(previous_months)
        
        attendance_trend = recent_rate - previous_rate
        if attendance_trend > 5:
            trend_direction = 'improving'
        elif attendance_trend < -5:
            trend_direction = 'declining'
        else:
            trend_direction = 'stable'
    else:
        attendance_trend = 0
        trend_direction = 'insufficient_data'
    
    response_data = {
        'student_id': student.id,
        'student_name': student.name,
        'section': student.section,
        'attendance_trends': monthly_trends,
        'total_sessions': total_sessions,
        'overall_attendance_rate': overall_attendance_rate,
        'status_breakdown': status_counts,
        'attendance_trend': round(attendance_trend, 2),
        'trend_direction': trend_direction,
        'latest_session_date': attendances.last().session.date if attendances.exists() else None,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_comprehensive_history_view(request, student_id):
    """Get comprehensive student history including health, fitness, and attendance"""
    user = request.user
    
    # Check permissions (same as other endpoints)
    if getattr(user, 'role', None) == 'TEACHER':
        assigned_sections = TeacherSection.objects.filter(
            teacher=user
        ).values_list('section', flat=True)
        
        try:
            student = Student.objects.get(id=student_id, section__in=assigned_sections)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not in your assigned sections.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'PARENT':
        try:
            student = Student.objects.get(id=student_id, parent=user)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not your child.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'ADMIN':
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {'detail': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get current health record
    try:
        current_health_record = HealthRecord.objects.get(student=student)
    except HealthRecord.DoesNotExist:
        current_health_record = None
    
    # Get health history
    health_history = HealthHistory.objects.filter(
        student=student
    ).order_by('date')
    
    # Get fitness performances
    performances = FitnessPerformance.objects.filter(
        student=student
    ).order_by('-date')[:20]  # Last 20 performances
    
    # Get attendance records
    attendances = Attendance.objects.filter(
        student=student
    ).select_related('session').order_by('-session__date')[:50]  # Last 50 attendances
    
    # Build comprehensive response
    response_data = {
        'student_id': student.id,
        'student_name': student.name,
        'section': student.section,
        'roll_number': student.roll_number,
        'current_health_record': {
            'height': current_health_record.height,
            'weight': current_health_record.weight,
            'bmi': current_health_record.bmi,
            'fitness_status': current_health_record.fitness_status,
            'ai_recommendations': current_health_record.ai_recommendations,
            'updated_at': current_health_record.updated_at,
        } if current_health_record else None,
        'health_history': [
            {
                'date': record.date,
                'height': record.height,
                'weight': record.weight,
                'bmi': record.bmi,
                'fitness_status': record.fitness_status,
            }
            for record in health_history
        ],
        'fitness_performances': [
            {
                'date': performance.date,
                'metric_name': performance.metric_name,
                'score': performance.score,
            }
            for performance in performances
        ],
        'attendance_records': [
            {
                'date': attendance.session.date,
                'session_name': attendance.session.name,
                'status': attendance.status,
                'notes': attendance.notes,
                'marked_at': attendance.marked_at,
            }
            for attendance in attendances
        ],
        'summary': {
            'total_health_records': health_history.count() + (1 if current_health_record else 0),
            'total_fitness_tests': performances.count(),
            'total_attendance_records': attendances.count(),
            'latest_health_update': current_health_record.updated_at if current_health_record else None,
            'latest_fitness_test': performances.first().date if performances.exists() else None,
            'latest_attendance': attendances.first().session.date if attendances.exists() else None,
        }
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# Report Generation Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_student_report_view(request, student_id):
    """Generate downloadable PDF report for a student"""
    user = request.user
    
    # Check permissions
    if getattr(user, 'role', None) == 'TEACHER':
        # Teachers can only access students in their assigned sections
        assigned_sections = TeacherSection.objects.filter(
            teacher=user
        ).values_list('section', flat=True)
        
        try:
            student = Student.objects.get(id=student_id, section__in=assigned_sections)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not in your assigned sections.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'PARENT':
        # Parents can only access their own children
        try:
            student = Student.objects.get(id=student_id, parent=user)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found or not your child.'},
                status=status.HTTP_404_NOT_FOUND
            )
    elif getattr(user, 'role', None) == 'ADMIN':
        # Admins can access any student
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {'detail': 'Student not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {'detail': 'Permission denied.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Get student data
        health_record = HealthRecord.objects.filter(student=student).first()
        health_history = HealthHistory.objects.filter(student=student).order_by('-date')
        fitness_performances = FitnessPerformance.objects.filter(student=student).order_by('-date')
        
        # Generate PDF
        pdf_content = generate_student_pdf(student, health_record, health_history, fitness_performances)
        
        # Prepare response
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="student_report_{student.name}_{student.roll_number}.pdf"'
        response['Content-Length'] = len(pdf_content)
        
        return response
        
    except Exception as e:
        return Response(
            {'detail': f'Error generating report: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

