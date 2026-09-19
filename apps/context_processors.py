from .permissions import get_user_role, Role
from .models import Notification

def user_role_context(request):
    """Context processor providing user role, unread notification count, and current role flags."""
    if not request.user.is_authenticated:
        return {
            'user_role': None,
            'unread_notifications_count': 0,
            'is_admin': False,
            'is_teacher': False,
            'is_student': False,
            'is_parent': False,
            'is_accountant': False,
            'is_receptionist': False,
        }

    role = get_user_role(request.user)
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return {
        'user_role': role,
        'unread_notifications_count': unread_count,
        'is_admin': role in (Role.SUPER_ADMIN, Role.ADMIN),
        'is_teacher': role in (Role.SUPER_ADMIN, Role.ADMIN, Role.TEACHER),
        'is_student': role == Role.STUDENT,
        'is_parent': role == Role.PARENT,
        'is_accountant': role in (Role.SUPER_ADMIN, Role.ADMIN, Role.ACCOUNTANT),
        'is_receptionist': role in (Role.SUPER_ADMIN, Role.ADMIN, Role.RECEPTIONIST),
    }
