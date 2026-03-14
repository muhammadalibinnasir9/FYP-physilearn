from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from .models import Notification, NotificationPreference

# Get the custom User model
User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """Create default notification preferences for new users"""
    
    if created:
        NotificationPreference.objects.get_or_create(user=instance)

def create_health_alert_notification(user, alert_type, message, priority="HIGH", student_id=None):
    """Helper function to create health alert notifications"""
    
    Notification.objects.create(
        title=f"Health Alert: {alert_type}",
        message=message,
        notification_type="HEALTH_ALERT",
        priority=priority,
        user=user,
        student_id=student_id,
        action_url=f"/students/{student_id}/" if student_id else None,
        action_text="View Health Data"
    )

def create_system_notification(users, title, message, priority="MEDIUM", action_url=None, action_text=None):
    """Helper function to create system-wide notifications"""
    
    notifications = []
    for user in users:
        notifications.append(
            Notification(
                title=title,
                message=message,
                notification_type="SYSTEM_UPDATE",
                priority=priority,
                user=user,
                action_url=action_url,
                action_text=action_text,
                expires_at=timezone.now() + timezone.timedelta(days=7)  # Expire after 7 days
            )
        )
    
    Notification.objects.bulk_create(notifications)


def send_credential_brief_notification(user, role_label):
    """
    Send an in-app credential brief to a newly created user (Teacher or Parent).
    Does not include the temporary password; they use the one provided by the admin.
    """
    title = "Your PhysiLearn account is ready"
    message = (
        f"Your {role_label} account has been created. "
        "Log in using your email and the temporary password provided by your administrator. "
        "You can change your password after signing in."
    )
    create_system_notification(
        users=[user],
        title=title,
        message=message,
        priority="HIGH",
        action_url="/login",
        action_text="Log in",
    )

def create_announcement_notification(user_roles, title, message, priority="MEDIUM"):
    """Helper function to create role-specific announcements"""
    
    # Placeholder for role-based user filtering
    users = User.objects.all()  # Simplified - would filter by role in real implementation
    create_system_notification(
        users=users,
        title=title,
        message=message,
        priority=priority,
        notification_type="ANNOUNCEMENT"
    )

# Custom signal for health record updates
def health_record_updated(sender, user, health_data, **kwargs):
    """Signal handler for health record updates"""
    
    # Check for concerning health metrics
    if health_data.get('heart_rate') and health_data['heart_rate'] > 100:
        create_health_alert_notification(
            user=user,
            alert_type="High Heart Rate",
            message=f"High heart rate detected: {health_data['heart_rate']} bpm",
            priority="URGENT"
        )
    
    if health_data.get('bmi') and health_data['bmi'] > 25:
        create_health_alert_notification(
            user=user,
            alert_type="BMI Alert",
            message=f"BMI above normal range: {health_data['bmi']}",
            priority="HIGH"
        )

# Custom signal for fitness performance updates
def fitness_performance_updated(sender, user, performance_data, **kwargs):
    """Signal handler for fitness performance updates"""
    
    # Notify about significant improvements or concerns
    if performance_data.get('score') and performance_data['score'] < 60:
        create_health_alert_notification(
            user=user,
            alert_type="Performance Concern",
            message=f"Low performance score in {performance_data.get('metric_name', 'exercise')}: {performance_data['score']}%",
            priority="MEDIUM"
        )

# Placeholder signals for student assignment (would be implemented when students model exists)
def student_assigned_to_teacher(sender, teacher_id, student_id, student_name, **kwargs):
    """Signal for when a student is assigned to a teacher"""
    try:
        teacher = User.objects.get(id=teacher_id)
        Notification.objects.create(
            title="New Student Assigned",
            message=f"New student {student_name} has been added to your roster.",
            notification_type="STUDENT_ASSIGNED",
            priority="MEDIUM",
            user=teacher,
            student_id=student_id,
            action_url=f"/students/{student_id}/",
            action_text="View Student"
        )
    except User.DoesNotExist:
        pass

def teacher_assigned_to_student(sender, parent_id, student_id, student_name, teacher_name, **kwargs):
    """Signal for when a teacher is assigned to a student's parent"""
    try:
        parent = User.objects.get(id=parent_id)
        Notification.objects.create(
            title="Teacher Assignment Updated",
            message=f"Coach {teacher_name} is now managing your child {student_name}'s physical education.",
            notification_type="TEACHER_ASSIGNED",
            priority="HIGH",
            user=parent,
            student_id=student_id,
            action_url=f"/students/{student_id}/",
            action_text="View Child's Profile"
        )
    except User.DoesNotExist:
        pass
