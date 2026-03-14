from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """Only users with role ADMIN or is_staff=True can access admin management endpoints."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            getattr(request.user, 'role', None) == 'ADMIN' or
            getattr(request.user, 'is_staff', False) is True
        )

class IsTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'TEACHER'

class IsParent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'PARENT'

class IsOwnerOrStaff(permissions.BasePermission):
    """
    Custom permission to only allow parents to see their own children
    and teachers to see their assigned students.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'ADMIN':
            return True
            
        student = obj.student if hasattr(obj, 'student') else obj
            
        if request.user.role == 'PARENT':
            # Parent has read-only access to their own children
            if request.method in permissions.SAFE_METHODS:
                return student.parent == request.user
            return False
        if request.user.role == 'TEACHER':
            # Teacher can view/edit their assigned students
            return student.teacher == request.user
        return False

