from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from domain.publishing.snapshots import release_previous_next


class PublishedReaderNavigationTests(SimpleTestCase):
    def test_reader_navigation_uses_units_not_non_lesson_activities(self) -> None:
        outline = [
            {
                "id": "module-1",
                "title": "Módulo 1",
                "activities": [
                    {"id": "unit-1", "title": "Lección 1", "type": "lesson"},
                    {
                        "id": "live-class-1",
                        "title": "Clase en vivo",
                        "type": "live_class",
                    },
                    {
                        "id": "assessment-1",
                        "title": "Evaluación",
                        "type": "assessment",
                    },
                    {"id": "unit-2", "title": "Lección 2", "type": "lesson"},
                ],
                "units": [
                    {"id": "unit-1", "title": "Lección 1"},
                    {"id": "unit-2", "title": "Lección 2"},
                ],
            }
        ]

        with patch("domain.publishing.snapshots.release_outline", return_value=outline):
            navigation = release_previous_next({}, "unit-1")

        self.assertEqual(navigation["position"], 1)
        self.assertEqual(navigation["total"], 2)
        self.assertIsNone(navigation["previous"])
        self.assertEqual(navigation["next"]["id"], "unit-2")
