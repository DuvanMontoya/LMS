from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from domain.identity.models import User


class UserModelTests(TestCase):
    def test_custom_user_model_has_uuid_email_identity_and_no_username(self) -> None:
        user = get_user_model().objects.create_user(" Person@Example.COM ")

        self.assertIs(get_user_model(), User)
        self.assertIsInstance(user.pk, uuid.UUID)
        self.assertEqual(user.email, "person@example.com")
        self.assertEqual(User.USERNAME_FIELD, "email")
        self.assertEqual(User.EMAIL_FIELD, "email")
        self.assertEqual(User.REQUIRED_FIELDS, [])
        self.assertNotIn("username", {field.name for field in User._meta.fields})
        self.assertTrue(user.has_usable_password() is False)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_passwords_use_argon2_and_validate_correctly(self) -> None:
        user = User.objects.create_user("password@example.com", "not-a-plain-password")

        self.assertNotEqual(user.password, "not-a-plain-password")
        self.assertTrue(user.password.startswith("argon2$"))
        self.assertTrue(user.check_password("not-a-plain-password"))
        self.assertFalse(user.check_password("incorrect-password"))

    def test_email_must_be_present_and_valid(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_user("   ")
        with self.assertRaises(ValidationError):
            User.objects.create_user("not-an-email")

    def test_email_is_unique_case_insensitively_in_postgresql(self) -> None:
        User.objects.create_user("duplicate@example.com")

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="DUPLICATE@EXAMPLE.COM")

    def test_natural_key_lookup_is_case_insensitive(self) -> None:
        user = User.objects.create_user("lookup@example.com")

        self.assertEqual(User.objects.get_by_natural_key("LOOKUP@example.com"), user)

    def test_names_and_string_representation_are_trimmed(self) -> None:
        user = User.objects.create_user(
            "name@example.com", first_name=" Ada ", last_name=" Lovelace "
        )

        self.assertEqual(user.get_full_name(), "Ada Lovelace")
        self.assertEqual(user.get_short_name(), "Ada")
        self.assertEqual(str(user), "name@example.com")
