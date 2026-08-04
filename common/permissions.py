from datetime import timedelta
from django.utils import timezone
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuth(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and not request.user.is_staff
        )


class IsAnon(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(not request.user or not request.user.is_authenticated)
        return False


class IsModerator(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_staff):
            return False

        if request.method == 'POST':
            return False

        return True


class CanEditWithIn15Minutes(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'created_at') or not obj.created_at:
            return True
        return timezone.now() - obj.created_at <= timedelta(minutes=15)