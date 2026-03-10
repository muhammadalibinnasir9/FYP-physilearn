from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    heartbeat, RegisterView, StudentListView, StudentDetailView, 
    StudentReportView, ClassSummaryView, HealthRecordViewSet, FitnessPerformanceViewSet,
    UserViewSet
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
router = DefaultRouter()
router.register(r'health-records', HealthRecordViewSet, basename='healthrecord')
router.register(r'fitness-performances', FitnessPerformanceViewSet, basename='fitnessperformance')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('heartbeat/', heartbeat, name='heartbeat'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('students/', StudentListView.as_view(), name='student_list'),
    path('students/<int:pk>/', StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:pk>/report/', StudentReportView.as_view(), name='student_report'),
    path('class-summary/', ClassSummaryView, name='class_summary'),
]


