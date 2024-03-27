from django.contrib.auth.forms import UserCreationForm
from .models import User


class SignUpForm(UserCreationForm):
    """Formulario para el registro de usuarios."""
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2',]
