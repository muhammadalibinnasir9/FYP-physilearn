from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

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
        if request.user.role == 'PARENT':
            # Parent has read-only access to their own children
            if request.method in permissions.SAFE_METHODS:
                return obj.parent == request.user
            return False
        if request.user.role == 'TEACHER':
            # Teacher can view/edit their assigned students
            return obj.teacher == request.user
        return False

