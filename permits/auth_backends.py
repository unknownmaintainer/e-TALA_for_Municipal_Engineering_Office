from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import CustomUser


class EmailBackend(ModelBackend):
    """Authenticate using email or username (case-insensitive)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None
        try:
            user = CustomUser.objects.filter(
                Q(email__iexact=username) | Q(username__iexact=username)
            ).first()
        except Exception:
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
