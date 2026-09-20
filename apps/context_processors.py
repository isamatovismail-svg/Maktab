from .permissions import get_user_role, Role

def user_role_context(request):
    """Context processor providing user role and current role flags."""
    if not request.user.is_authenticated:
        return {
            'user_role': None,
            'is_admin': False,
            'is_teacher': False,
            'is_student': False,
        }

    role = get_user_role(request.user)

    return {
        'user_role': role,
        'is_admin': role == Role.ADMIN,
        'is_teacher': role == Role.TEACHER,
        'is_student': role == Role.STUDENT,
    }

