from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    heartbeat, RegisterView, UserViewSet, CustomTokenObtainPairView,
    logout_view, class_summary_view, user_profile_view, students_list_view, admin_analytics_view,
    HealthRecordViewSet, FitnessPerformanceViewSet,
    AcademicTermViewSet, FitnessTestParameterViewSet,
    StudentAdminViewSet,
    create_teacher_and_assign_sections_view,
    create_parent_and_link_students_view,
    teacher_sections_view,
    PESessionViewSet, AttendanceViewSet,
    bulk_attendance_view, attendance_analytics_view,
    student_health_history_view, student_fitness_progress_view,
    student_attendance_trends_view, student_comprehensive_history_view,
    generate_student_report_view
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'admin/students', StudentAdminViewSet, basename='admin-student')
router.register(r'health-records', HealthRecordViewSet, basename='health-record')
router.register(r'fitness-performances', FitnessPerformanceViewSet, basename='fitness-performance')
router.register(r'academic-terms', AcademicTermViewSet, basename='academic-term')
router.register(r'fitness-test-parameters', FitnessTestParameterViewSet, basename='fitness-test-parameter')
router.register(r'pe-sessions', PESessionViewSet, basename='pe-session')
router.register(r'attendance', AttendanceViewSet, basename='attendance')

urlpatterns = [
    path('heartbeat/', heartbeat, name='heartbeat'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', logout_view, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/profile/', user_profile_view, name='user_profile'),
    path('teacher/sections/', teacher_sections_view, name='teacher_sections'),
    path('admin/teachers/', create_teacher_and_assign_sections_view, name='admin_create_teacher_assign_sections'),
    path('admin/parents/', create_parent_and_link_students_view, name='admin_create_parent_link_students'),
    path('students/', students_list_view, name='students_list'),
    path('students/my-children', my_children_view, name='my_children'),
    path('admin/analytics/', admin_analytics_view, name='admin_analytics'),
    path('class-summary/', class_summary_view, name='class_summary'),
    path('attendance/bulk/', bulk_attendance_view, name='bulk_attendance'),
    path('attendance/analytics/', attendance_analytics_view, name='attendance_analytics'),
    path('students/<int:student_id>/health-history/', student_health_history_view, name='student_health_history'),
    path('students/<int:student_id>/fitness-progress/', student_fitness_progress_view, name='student_fitness_progress'),
    path('students/<int:student_id>/attendance-trends/', student_attendance_trends_view, name='student_attendance_trends'),
    path('students/<int:student_id>/comprehensive-history/', student_comprehensive_history_view, name='student_comprehensive_history'),
    path('students/<int:student_id>/report/', generate_student_report_view, name='generate_student_report'),
    path('', include(router.urls)),
]


