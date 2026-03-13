from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationPreferenceViewSet, NotificationHistoryViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notification-preference')
router.register(r'notification-history', NotificationHistoryViewSet, basename='notification-history')

app_name = 'notifications'

urlpatterns = [
    path('', include(router.urls)),
]
