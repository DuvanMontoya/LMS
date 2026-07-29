from django.conf import settings
from django.test import SimpleTestCase


class ScaffoldingSettingsTests(SimpleTestCase):
    def test_uses_postgresql_without_sqlite_fallback(self) -> None:
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql"
        )

    def test_structural_apps_are_installed(self) -> None:
        expected_apps = {
            "domain.identity",
            "domain.catalog",
            "domain.content",
            "domain.learning",
            "domain.assessments",
        }
        self.assertTrue(expected_apps.issubset(settings.INSTALLED_APPS))
