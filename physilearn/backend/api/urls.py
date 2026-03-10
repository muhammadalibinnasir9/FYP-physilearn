from django.urls import path
from .views import heartbeat, RegisterView, StudentListView, StudentDetailView, StudentReportView, ClassSummaryView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    path('heartbeat/', heartbeat, name='heartbeat'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('students/', StudentListView.as_view(), name='student_list'),
    path('students/<int:pk>/', StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:pk>/report/', StudentReportView.as_view(), name='student_report'),
    path('class-summary/', ClassSummaryView, name='class_summary'),
]


