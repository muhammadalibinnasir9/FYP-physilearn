from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count, F
from django.conf import settings
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationPreferenceSerializer, UnreadNotificationCountSerializer,
    BulkNotificationSerializer, NotificationStatsSerializer
)

# Get the custom User model
User = settings.AUTH_USER_MODEL

class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notifications"""
    
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority', 'is_read']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter notifications based on user role and permissions"""
        user = self.request.user
        
        if user.is_superuser:
            return Notification.objects.all()
        
        # Base queryset - user's own notifications
        queryset = Notification.objects.filter(user=user)
        
        # Apply role-based permissions (simplified without students model)
        if hasattr(user, 'role') and user.role == 'TEACHER':
            # Teachers can see their own notifications
            queryset = queryset.filter(user=user)
        elif hasattr(user, 'role') and user.role == 'PARENT':
            # Parents can see their own notifications
            queryset = queryset.filter(user=user)
        
        # Filter out expired notifications
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def perform_create(self, serializer):
        """Create notification with user assignment validation"""
        user = self.request.user
        
        # Only admins can create notifications for other users
        if not user.is_superuser:
            serializer.save(user=user)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        queryset = self.get_queryset().filter(is_read=False)
        
        unread_count = queryset.count()
        urgent_count = queryset.filter(priority='URGENT').count()
        high_priority_count = queryset.filter(priority='HIGH').count()
        
        serializer = UnreadNotificationCountSerializer({
            'unread_count': unread_count,
            'urgent_count': urgent_count,
            'high_priority_count': high_priority_count
        })
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'message': 'Notification marked as read',
            'read_at': notification.read_at
        })
    
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark notification as unread"""
        notification = self.get_object()
        notification.is_read = False
        notification.read_at = None
        notification.save(update_fields=['is_read', 'read_at'])
        
        return Response({
            'message': 'Notification marked as unread'
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        queryset = self.get_queryset().filter(is_read=False)
        count = queryset.count()
        
        queryset.update(is_read=True, read_at=timezone.now())
        
        return Response({
            'message': f'Marked {count} notifications as read'
        })
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on notifications"""
        serializer = BulkNotificationSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        notification_ids = serializer.validated_data['notification_ids']
        action = serializer.validated_data['action']
        
        queryset = self.get_queryset().filter(id__in=notification_ids)
        
        if action == 'mark_read':
            queryset.update(is_read=True, read_at=timezone.now())
            message = f'Marked {len(notification_ids)} notifications as read'
        
        elif action == 'mark_unread':
            queryset.update(is_read=False, read_at=None)
            message = f'Marked {len(notification_ids)} notifications as unread'
        
        elif action == 'delete':
            count = queryset.count()
            queryset.delete()
            message = f'Deleted {count} notifications'
        
        return Response({'message': message})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics"""
        queryset = self.get_queryset()
        
        total_notifications = queryset.count()
        unread_notifications = queryset.filter(is_read=False).count()
        read_notifications = queryset.filter(is_read=True).count()
        
        # Notifications by type
        notifications_by_type = queryset.values('notification_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        notifications_by_type_dict = {
            item['notification_type']: item['count'] 
            for item in notifications_by_type
        }
        
        # Notifications by priority
        notifications_by_priority = queryset.values('priority').annotate(
            count=Count('id')
        ).order_by('-count')
        
        notifications_by_priority_dict = {
            item['priority']: item['count'] 
            for item in notifications_by_priority
        }
        
        # Recent notifications
        recent_notifications = queryset.order_by('-created_at')[:5]
        
        serializer = NotificationStatsSerializer({
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'read_notifications': read_notifications,
            'notifications_by_type': notifications_by_type_dict,
            'notifications_by_priority': notifications_by_priority_dict,
            'recent_notifications': recent_notifications
        })
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'])
    def cleanup_expired(self, request):
        """Delete expired notifications"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only admins can cleanup notifications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        expired_count = Notification.objects.filter(
            expires_at__lt=timezone.now()
        ).count()
        
        Notification.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()
        
        return Response({
            'message': f'Deleted {expired_count} expired notifications'
        })

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notification preferences"""
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only manage their own preferences"""
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create preferences for the authenticated user"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_preferences(self, request):
        """Get current user's notification preferences"""
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def test_notification(self, request):
        """Send a test notification to the user"""
        user = request.user
        
        Notification.objects.create(
            title="Test Notification",
            message="This is a test notification to verify your notification settings.",
            notification_type="SYSTEM_UPDATE",
            priority="LOW",
            user=user,
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )
        
        return Response({
            'message': 'Test notification sent successfully'
        })

class NotificationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing notification history (read-only)"""
    
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'read_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get read notifications for history"""
        return NotificationViewSet.get_queryset(self).filter(is_read=True)
    
    @action(detail=False, methods=['get'])
    def digest(self, request):
        """Get daily/weekly notification digest"""
        days = int(request.query_params.get('days', 7))
        
        since_date = timezone.now() - timezone.timedelta(days=days)
        queryset = self.get_queryset().filter(created_at__gte=since_date)
        
        # Group by date
        notifications_by_date = {}
        for notification in queryset:
            date_str = notification.created_at.strftime('%Y-%m-%d')
            if date_str not in notifications_by_date:
                notifications_by_date[date_str] = []
            notifications_by_date[date_str].append(
                NotificationSerializer(notification).data
            )
        
        return Response({
            'period_days': days,
            'total_notifications': queryset.count(),
            'notifications_by_date': notifications_by_date
        })
