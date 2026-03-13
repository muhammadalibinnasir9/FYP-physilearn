from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
import uuid

# Get the custom User model
User = settings.AUTH_USER_MODEL

class Notification(models.Model):
    """Notification model for role-specific alerts"""
    
    NOTIFICATION_TYPES = [
        ('STUDENT_ASSIGNED', 'Student Assigned'),
        ('TEACHER_ASSIGNED', 'Teacher Assigned'),
        ('HEALTH_ALERT', 'Health Alert'),
        ('SYSTEM_UPDATE', 'System Update'),
        ('ANNOUNCEMENT', 'Announcement'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='MEDIUM')
    
    # Target user
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    # Related objects (optional - using string references to avoid circular imports)
    student_id = models.IntegerField(null=True, blank=True, help_text="Reference to student ID")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='teacher_notifications')
    
    # Status and timestamps
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Action URLs
    action_url = models.URLField(max_length=500, blank=True, null=True)
    action_text = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['notification_type', 'priority']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def clean(self):
        """Validate notification data"""
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError("Expiration date must be in the future")
        
        if self.notification_type == 'STUDENT_ASSIGNED' and not self.student_id:
            raise ValidationError("Student assignment notifications must include a student")
        
        if self.notification_type == 'TEACHER_ASSIGNED' and not self.teacher:
            raise ValidationError("Teacher assignment notifications must include a teacher")
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def is_expired(self):
        """Check if notification is expired"""
        return self.expires_at and self.expires_at <= timezone.now()
    
    def get_display_color(self):
        """Get color based on priority"""
        colors = {
            'LOW': '#6c757d',
            'MEDIUM': '#17a2b8',
            'HIGH': '#fd7e14',
            'URGENT': '#dc3545',
        }
        return colors.get(self.priority, '#6c757d')
    
    def get_icon(self):
        """Get icon based on notification type"""
        icons = {
            'STUDENT_ASSIGNED': 'person_add',
            'TEACHER_ASSIGNED': 'school',
            'HEALTH_ALERT': 'medical_services',
            'SYSTEM_UPDATE': 'system_update',
            'ANNOUNCEMENT': 'campaign',
        }
        return icons.get(self.notification_type, 'notifications')

class NotificationPreference(models.Model):
    """User notification preferences"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_notifications = models.BooleanField(default=True)
    email_health_alerts = models.BooleanField(default=True)
    email_student_updates = models.BooleanField(default=True)
    
    # Push notification preferences
    push_notifications = models.BooleanField(default=True)
    push_health_alerts = models.BooleanField(default=True)
    push_student_updates = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default=models.TimeField(22, 0, 0))
    quiet_hours_end = models.TimeField(default=models.TimeField(8, 0, 0))
    
    # Auto-delete settings
    auto_delete_read = models.BooleanField(default=True)
    auto_delete_after_days = models.PositiveIntegerField(default=30)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled:
            return False
        
        current_time = timezone.now().time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day (e.g., 22:00 to 08:00)
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:
            # Overnight (e.g., 22:00 to 08:00 next day)
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end
    
    def should_send_notification(self, notification_type, priority):
        """Check if notification should be sent based on preferences"""
        if self.is_quiet_hours() and priority != 'URGENT':
            return False
        
        if notification_type == 'HEALTH_ALERT':
            return self.email_health_alerts if self.email_notifications else False
        
        if notification_type in ['STUDENT_ASSIGNED', 'TEACHER_ASSIGNED']:
            return self.email_student_updates if self.email_notifications else False
        
        return self.email_notifications
