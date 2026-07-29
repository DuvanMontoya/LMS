from __future__ import annotations

from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

from .models import User


class UserCreationForm(DjangoUserCreationForm):  # pyright: ignore[reportMissingTypeArgument]
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        return User.objects.normalize_email_address(email)


class UserChangeForm(DjangoUserChangeForm):  # pyright: ignore[reportMissingTypeArgument]
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"
