import functools
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def role_required(allowed_roles):
    """
    Decorator for view functions to enforce user role permissions.
    allowed_roles can be a list or tuple of role strings, e.g. ['admin', 'staff'].
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('login')
            if request.user.role not in allowed_roles:
                raise PermissionDenied("You do not have permission to access this resource.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator requiring administrator role for view functions."""
    return role_required(['admin'])(view_func)


def staff_or_admin_required(view_func):
    """Decorator requiring staff or administrator role for view functions."""
    return role_required(['staff', 'admin'])(view_func)


def has_role(user, allowed_roles):
    """Utility function to check if a user instance has one of the allowed roles."""
    if not user or not user.is_authenticated:
        return False
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    return user.role in allowed_roles
