from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class ContentDemoCommandTests(SimpleTestCase):
    @override_settings(DEBUG=False)
    def test_bootstrap_rejects_non_development_settings(self) -> None:
        with self.assertRaisesMessage(
            CommandError, "El contenido demo sólo se permite con DEBUG=True."
        ):
            call_command("bootstrap_demo_content")
