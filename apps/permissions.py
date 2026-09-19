import logging
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger('apps')

class Role:
    SUPER_ADMIN = 'SUPER_ADMIN'
    ADMIN = 'ADMIN'
    TEACHER = 'TEACHER'
    ACCOUNTANT = 'ACCOUNTANT'
    RECEPTIONIST = 'RECEPTIONIST'
    STUDENT = 'STUDENT'
    PARENT = 'PARENT'

    CHOICES = [
        (SUPER_ADMIN, 'Super Admin'),
        (ADMIN, 'Administrator'),
        (TEACHER, "O'qituvchi"),
        (ACCOUNTANT, 'Hisobchi (Accountant)'),
        (RECEPTIONIST, 'Qabulxona (Receptionist)'),
        (STUDENT, "O'quvchi"),
        (PARENT, 'Ota-ona (Parent)'),
    ]

def get_user_role(user):
    """Determine user's system role based on profile association or flags."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return Role.SUPER_ADMIN

    # Check UserProfile if linked
    if hasattr(user, 'profile') and user.profile.role:
        return user.profile.role

    # Fallbacks based on profiles
    if hasattr(user, 'teacher_profile'):
        return Role.TEACHER
    if hasattr(user, 'student_profile'):
        return Role.STUDENT
    if hasattr(user, 'parent_profile'):
        return Role.PARENT

    if user.is_staff:
        return Role.ADMIN

    return Role.STUDENT

class RoleRequiredMixin(AccessMixin):
    """CBV Mixin to enforce role restrictions."""
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        user_role = get_user_role(request.user)
        if self.allowed_roles and user_role not in self.allowed_roles and user_role != Role.SUPER_ADMIN:
            logger.warning(
                f"Unauthorized role access attempt: user={request.user.username}, role={user_role}, path={request.path}"
            )
            messages.error(request, "Ushbu sahifaga kirish uchun sizda yetarli ruxsat yo'q!")
            raise PermissionDenied("Ruxsat berilmagan sahifa.")
        return super().dispatch(request, *args, **kwargs)

def role_required(*allowed_roles):
    """FBV Decorator to enforce role restrictions."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            user_role = get_user_role(request.user)
            if allowed_roles and user_role not in allowed_roles and user_role != Role.SUPER_ADMIN:
                logger.warning(
                    f"Unauthorized role access attempt: user={request.user.username}, role={user_role}, path={request.path}"
                )
                messages.error(request, "Ushbu sahifaga kirish uchun sizda yetarli ruxsat yo'q!")
                raise PermissionDenied("Ruxsat berilmagan sahifa.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
