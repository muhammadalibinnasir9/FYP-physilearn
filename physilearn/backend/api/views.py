from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics, viewsets
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer, UserSerializer, StudentSerializer, HealthRecordSerializer, FitnessPerformanceSerializer
from .models import Student, HealthRecord, HealthHistory, FitnessPerformance
from .permissions import IsOwnerOrStaff, IsAdmin, IsTeacher, IsParent
from .reports import generate_student_pdf
from django.db.models import Avg
from django.http import HttpResponse

from django.contrib.auth import get_user_model

User = get_user_model()

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

class StudentListView(generics.ListCreateAPIView):
    serializer_class = StudentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return Student.objects.all()
        if user.role == 'TEACHER':
            return Student.objects.filter(teacher=user)
        if user.role == 'PARENT':
            return Student.objects.filter(parent=user)
        return Student.objects.none()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        return UserSerializer

class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsOwnerOrStaff]

class HealthRecordViewSet(viewsets.ModelViewSet):
    serializer_class = HealthRecordSerializer
    permission_classes = [IsOwnerOrStaff]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return HealthRecord.objects.all()
        if user.role == 'TEACHER':
            return HealthRecord.objects.filter(student__teacher=user)
        if user.role == 'PARENT':
            return HealthRecord.objects.filter(student__parent=user)
        return HealthRecord.objects.none()

class FitnessPerformanceViewSet(viewsets.ModelViewSet):
    serializer_class = FitnessPerformanceSerializer
    permission_classes = [IsOwnerOrStaff]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return FitnessPerformance.objects.all()
        if user.role == 'TEACHER':
            return FitnessPerformance.objects.filter(student__teacher=user)
        if user.role == 'PARENT':
            return FitnessPerformance.objects.filter(student__parent=user)
        return FitnessPerformance.objects.none()

class StudentReportView(generics.GenericAPIView):
    permission_classes = [IsOwnerOrStaff]

    def get(self, request, pk):
        try:
            student = Student.objects.get(pk=pk)
            self.check_object_permissions(request, student)
            
            health_record = student.health_record
            history = student.health_history.all()
            performances = student.performances.all()
            
            pdf_content = generate_student_pdf(student, health_record, history, performances)
            
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="progress_report_{student.roll_number}.pdf"'
            response.write(pdf_content)
            return response
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        except HealthRecord.DoesNotExist:
            return Response({"error": "No health record found for this student"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsTeacher | IsAdmin])
def ClassSummaryView(request):
    user = request.user
    if user.role == 'ADMIN':
        students = Student.objects.all()
    else:
        students = Student.objects.filter(teacher=user)
    
    bmis = []
    for s in students:
        try:
            bmis.append(s.health_record.bmi)
        except:
            continue
    
    avg_bmi = sum(bmis) / len(bmis) if bmis else 0
    participation_rate = (len(bmis) / students.count() * 100) if students.count() > 0 else 0
    
    return Response({
        "average_bmi": round(avg_bmi, 2),
        "participation_rate": round(participation_rate, 2),
        "total_students": students.count(),
        "records_collected": len(bmis)
    })

