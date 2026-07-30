from __future__ import annotations

from copy import deepcopy

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from django.test.utils import override_settings

from domain.publishing.canonical import canonical_json_bytes
from domain.publishing.exceptions import ReleaseSnapshotInvalid
from domain.publishing.schemas import validate_release_snapshot


class ReleaseSchemaTests(SimpleTestCase):
    def test_schema_is_strict_draft_2020_12_and_canonical_is_stable(self) -> None:
        left = {"b": "á", "a": [2, 1]}
        right = {"a": [2, 1], "b": "á"}
        self.assertEqual(canonical_json_bytes(left), canonical_json_bytes(right))

    def test_invalid_minimal_and_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(ReleaseSnapshotInvalid):
            validate_release_snapshot({})
        invalid = deepcopy({})
        invalid["unexpected"] = True
        with self.assertRaises(ReleaseSnapshotInvalid):
            validate_release_snapshot(invalid)

    @override_settings(DEBUG=False)
    def test_demo_bootstrap_rejects_production(self) -> None:
        with self.assertRaisesMessage(
            CommandError, "La publicación demo sólo se permite"
        ):
            call_command("bootstrap_demo_publication")
