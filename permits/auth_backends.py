from django.contrib.auth.backends import ModelBackend
from .models import CustomUser


class EmailBackend(ModelBackend):
    """Authenticate using email instead of username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            return None
        if user.check_password(password):
            return user
        return None
