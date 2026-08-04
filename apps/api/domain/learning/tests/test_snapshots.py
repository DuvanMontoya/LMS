import uuid
from unittest.mock import patch

from django.test import SimpleTestCase

from domain.learning.exceptions import LearningUnitNotFound
from domain.learning.snapshots import snapshot_activity_navigation


class ActivitySnapshotNavigationTests(SimpleTestCase):
    def setUp(self) -> None:
        self.lesson_id = uuid.uuid4()
        self.assessment_id = uuid.uuid4()
        self.outline = [
            {
                "id": str(uuid.uuid4()),
                "title": "Módulo",
                "activities": [
                    {
                        "id": str(self.lesson_id),
                        "title": "Lección",
                        "type": "lesson",
                    },
                    {
                        "id": str(self.assessment_id),
                        "title": "Evaluación",
                        "type": "assessment",
                    },
                ],
            }
        ]

    @patch("domain.learning.snapshots.snapshot_outline")
    def test_navigates_the_activity_sequence_including_assessments(
        self, snapshot_outline
    ) -> None:
        snapshot_outline.return_value = self.outline

        navigation = snapshot_activity_navigation(object(), self.assessment_id)

        self.assertEqual(navigation["position"], 2)
        self.assertEqual(navigation["total"], 2)
        self.assertEqual(navigation["previous"]["id"], str(self.lesson_id))
        self.assertIsNone(navigation["next"])

    @patch("domain.learning.snapshots.snapshot_outline")
    def test_rejects_an_activity_outside_the_release(self, snapshot_outline) -> None:
        snapshot_outline.return_value = self.outline

        with self.assertRaises(LearningUnitNotFound):
            snapshot_activity_navigation(object(), uuid.uuid4())
