from __future__ import annotations

from django.contrib import admin
from django.test import RequestFactory, TestCase

from domain.identity.admin import UserAdmin
from domain.identity.models import User


class UserAdminTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.admin = admin.site._registry[User]

    def test_custom_user_admin_is_registered_and_searches_email(self) -> None:
        user = User.objects.create_user("search@example.com")
        queryset, _ = self.admin.get_search_results(
            self.factory.get("/admin/"), User.objects.all(), "search@example.com"
        )

        self.assertIsInstance(self.admin, UserAdmin)
        self.assertEqual(list(queryset), [user])
        self.assertIn("email", self.admin.list_display)
        self.assertNotIn("username", self.admin.search_fields)

    def test_admin_requires_staff_and_allows_staff(self) -> None:
        anonymous = self.client.get("/admin/")
        self.assertEqual(anonymous.status_code, 302)

        non_staff = User.objects.create_user(
            "non-staff@example.com", "secure-test-password"
        )
        self.client.force_login(non_staff)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

        staff = User.objects.create_user(
            "staff@example.com", "secure-test-password", is_staff=True
        )
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
