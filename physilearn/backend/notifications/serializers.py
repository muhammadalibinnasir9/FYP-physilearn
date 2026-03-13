from rest_framework import serializers
from django.conf import settings
from .models import Notification, NotificationPreference
from django.utils import timezone

# Get the custom User model
User = settings.AUTH_USER_MODEL

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for notification context"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    user_details = UserSerializer(source='user', read_only=True)
    student_name = serializers.CharField(read_only=True)
    teacher_name = serializers.SerializerMethodField()
    display_color = serializers.CharField(read_only=True)
    icon = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'priority',
            'user', 'user_details', 'student_id', 'student_name', 
            'teacher', 'teacher_name', 'is_read', 'created_at', 
            'read_at', 'expires_at', 'action_url', 'action_text',
            'display_color', 'icon', 'is_expired'
        ]
        read_only_fields = ['id', 'created_at', 'read_at', 'display_color', 'icon', 'is_expired']
    
    def get_teacher_name(self, obj):
        """Get teacher's full name"""
        if obj.teacher:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}".strip() or obj.teacher.username
        return None
    
    def validate(self, data):
        """Validate notification data"""
        if data.get('expires_at') and data['expires_at'] <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future")
        
        notification_type = data.get('notification_type')
        if notification_type == 'STUDENT_ASSIGNED' and not data.get('student_id'):
            raise serializers.ValidationError("Student assignment notifications must include a student")
        
        if notification_type == 'TEACHER_ASSIGNED' and not data.get('teacher'):
            raise serializers.ValidationError("Teacher assignment notifications must include a teacher")
        
        return data

class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications (admin only)"""
    
    class Meta:
        model = Notification
        fields = [
            'title', 'message', 'notification_type', 'priority',
            'user', 'student_id', 'teacher', 'expires_at', 
            'action_url', 'action_text'
        ]
    
    def create(self, validated_data):
        """Create notification with automatic user assignment if needed"""
        notification_type = validated_data.get('notification_type')
        
        # Auto-assign user based on notification type and related objects
        if notification_type == 'STUDENT_ASSIGNED' and validated_data.get('student_id'):
            # Placeholder logic - would need student model to implement properly
            pass
        elif notification_type == 'TEACHER_ASSIGNED' and validated_data.get('student_id'):
            # Placeholder logic - would need student model to implement properly
            pass
        
        return super().create(validated_data)

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model"""
    
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'user', 'user_details', 'email_notifications', 'email_health_alerts',
            'email_student_updates', 'push_notifications', 'push_health_alerts',
            'push_student_updates', 'quiet_hours_enabled', 'quiet_hours_start',
            'quiet_hours_end', 'auto_delete_read', 'auto_delete_after_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

class UnreadNotificationCountSerializer(serializers.Serializer):
    """Serializer for unread notification count"""
    
    unread_count = serializers.IntegerField()
    urgent_count = serializers.IntegerField()
    high_priority_count = serializers.IntegerField()

class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notification operations"""
    
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=['mark_read', 'mark_unread', 'delete'])
    
    def validate_notification_ids(self, value):
        """Validate that all notification IDs exist and belong to user"""
        user = self.context['request'].user
        existing_notifications = Notification.objects.filter(
            id__in=value, 
            user=user
        ).values_list('id', flat=True)
        
        missing_ids = set(value) - set(existing_notifications)
        if missing_ids:
            raise serializers.ValidationError(
                f"Invalid notification IDs: {list(missing_ids)}"
            )
        
        return value

class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    read_notifications = serializers.IntegerField()
    notifications_by_type = serializers.DictField()
    notifications_by_priority = serializers.DictField()
    recent_notifications = NotificationSerializer(many=True)
