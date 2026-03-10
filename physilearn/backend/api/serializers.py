from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', User.PARENT)
        )
from .models import Student, HealthRecord, HealthHistory, FitnessPerformance

class HealthHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthHistory
        fields = ('date', 'height', 'weight', 'bmi', 'fitness_status')

class FitnessPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitnessPerformance
        fields = ('date', 'metric_name', 'score')


class HealthRecordSerializer(serializers.ModelSerializer):
    height = serializers.FloatField()
    weight = serializers.FloatField()
    bmi = serializers.FloatField(read_only=True)

    class Meta:
        model = HealthRecord
        fields = ('height', 'weight', 'bmi', 'fitness_status', 'ai_recommendations', 'activity_record', 'fitness_test_scores')


class StudentSerializer(serializers.ModelSerializer):
    health_record = HealthRecordSerializer(read_only=True)
    health_history = HealthHistorySerializer(many=True, read_only=True)
    performances = FitnessPerformanceSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ('id', 'name', 'roll_number', 'section', 'parent', 'teacher', 'health_record', 'health_history', 'performances')


