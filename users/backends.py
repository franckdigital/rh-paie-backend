from django.contrib.auth.backends import ModelBackend
from .models import User


class EmailOrUsernameBackend(ModelBackend):
    """Permet la connexion par email OU par nom d'utilisateur."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
