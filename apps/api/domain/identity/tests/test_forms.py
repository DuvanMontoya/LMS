from __future__ import annotations

from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.test import TestCase

from domain.identity.forms import UserChangeForm, UserCreationForm


class UserAdminFormTests(TestCase):
    def test_creation_form_uses_email_and_hashes_password(self) -> None:
        form = UserCreationForm(
            data={
                "email": " Form@Example.com ",
                "first_name": "Form",
                "last_name": "User",
                "password1": "secure-test-password",
                "password2": "secure-test-password",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "form@example.com")
        self.assertTrue(user.password.startswith("argon2$"))
        self.assertNotIn("username", form.fields)

    def test_change_form_keeps_password_as_a_read_only_hash(self) -> None:
        self.assertIsInstance(
            UserChangeForm.base_fields["password"], ReadOnlyPasswordHashField
        )
        self.assertNotIn("username", UserChangeForm.base_fields)
