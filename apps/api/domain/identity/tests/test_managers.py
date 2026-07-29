from __future__ import annotations

from django.test import TestCase

from domain.identity.models import User


class UserManagerTests(TestCase):
    def test_create_user_persists_with_database_alias(self) -> None:
        user = User.objects.db_manager("default").create_user("manager@example.com")

        self.assertEqual(User.objects.get(pk=user.pk).email, "manager@example.com")
        self.assertFalse(user.has_usable_password())

    def test_create_superuser_sets_required_flags(self) -> None:
        user = User.objects.create_superuser(
            "admin@example.com", "secure-test-password"
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_invalid_flags(self) -> None:
        with self.assertRaisesMessage(ValueError, "is_staff=True"):
            User.objects.create_superuser("staff@example.com", is_staff=False)
        with self.assertRaisesMessage(ValueError, "is_superuser=True"):
            User.objects.create_superuser("super@example.com", is_superuser=False)
