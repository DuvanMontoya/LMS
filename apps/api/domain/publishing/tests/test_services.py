from __future__ import annotations

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import TestCase

from domain.content.models import UnitContentDocument, UnitLessonResource
from domain.courses.choices import AuthoringStatus, LessonKind
from domain.courses.models import MediaCMSVideoBinding
from domain.courses.services import (
    approve_revision,
    confirm_completion_policy,
    submit_revision_for_review,
)
from domain.publishing.choices import PublicationEventType, PublicationStatus
from domain.publishing.exceptions import (
    PublicationConflict,
    PublicationTransitionInvalid,
)
from domain.publishing.integrity import verify_release, verify_release_chain
from domain.publishing.models import CoursePublicationEvent, CourseRelease
from domain.publishing.services import (
    create_draft_from_release,
    publish_approved_revision,
    withdraw_publication,
)

from .support import PublishingFixtureMixin


class PublicationServiceTests(PublishingFixtureMixin, TestCase):
    def test_typed_file_delivery_is_snapshot_only_and_cloned_without_document(
        self,
    ) -> None:
        (
            owner,
            organization,
            revision,
            _module,
            unit,
            _objective,
            _topic,
            publication,
            release,
        ) = self.published_context(lesson_kind=LessonKind.PDF)
        snapshot_unit = release.snapshot["modules"][0]["units"][0]
        self.assertEqual(snapshot_unit["delivery"]["kind"], "asset")
        self.assertNotIn("content", snapshot_unit)
        self.assertFalse(UnitContentDocument.objects.filter(unit=unit).exists())

        draft = create_draft_from_release(
            actor=owner,
            organization=organization,
            course=revision.course,
            release_number=release.number,
            expected_publication_version=publication.lock_version,
        )
        copied = UnitLessonResource.objects.get(unit__module__revision=draft)
        self.assertEqual(
            str(copied.asset_version_id), snapshot_unit["delivery"]["asset_version_id"]
        )

    def test_video_binding_is_release_pinned_and_copied_into_a_new_draft(self) -> None:
        (
            owner,
            organization,
            revision,
            _module,
            unit,
            _objective,
            _topic,
            publication,
            release,
        ) = self.published_context(lesson_kind=LessonKind.MEDIACMS_VIDEO)
        snapshot_unit = release.snapshot["modules"][0]["units"][0]
        self.assertEqual(snapshot_unit["lesson_kind"], LessonKind.MEDIACMS_VIDEO)
        self.assertEqual(
            snapshot_unit["delivery"],
            {
                "kind": "mediacms_lti",
                "media": {
                    "provider": "mediacms_lti",
                    "media_friendly_token": "ak7uPO2Vn",
                },
            },
        )
        self.assertNotIn("content", snapshot_unit)
        draft = create_draft_from_release(
            actor=owner,
            organization=organization,
            course=revision.course,
            release_number=release.number,
            expected_publication_version=publication.lock_version,
        )
        draft_binding = MediaCMSVideoBinding.objects.get(unit__module__revision=draft)
        self.assertEqual(draft_binding.media_friendly_token, "ak7uPO2Vn")
        self.assertNotEqual(draft_binding.unit_id, unit.id)

    def test_publish_builds_complete_snapshot_and_is_naturally_idempotent(self) -> None:
        owner, organization, revision, _module, unit, *_ = (
            self.approved_revision_context()
        )
        first = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=revision,
            expected_publication_version=0,
        )
        second = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=revision,
            expected_publication_version=1,
        )
        self.assertFalse(first.already_released)
        self.assertTrue(second.already_released)
        self.assertEqual(CourseRelease.objects.count(), 1)
        self.assertEqual(
            CoursePublicationEvent.objects.filter(
                event_type=PublicationEventType.RELEASE_PUBLISHED
            ).count(),
            1,
        )
        self.assertEqual(first.release.snapshot["release_number"], 1)
        self.assertIsNone(first.release.snapshot["previous_release_digest"])
        snapshot_unit = first.release.snapshot["modules"][0]["units"][0]
        self.assertEqual(snapshot_unit["id"], str(unit.id))
        self.assertEqual(
            snapshot_unit["delivery"]["content"]["document"]["type"], "doc"
        )
        self.assertNotIn("content", snapshot_unit)
        self.assertTrue(verify_release(first.release).valid)
        self.assertTrue(verify_release_chain(revision.course).valid)

    def test_conflict_with_stale_expected_version_rolls_back(self) -> None:
        owner, organization, revision, *_ = self.approved_revision_context()
        publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=revision,
            expected_publication_version=0,
        )
        with self.assertRaises(PublicationConflict):
            withdraw_publication(
                actor=owner,
                organization=organization,
                course=revision.course,
                expected_publication_version=0,
                note="Versión obsoleta.",
            )
        self.assertEqual(revision.course.publication.status, PublicationStatus.ACTIVE)

    def test_withdraw_is_terminal_until_a_new_release(self) -> None:
        owner, organization, revision, *_, publication, release = (
            self.published_context()
        )
        withdrawn = withdraw_publication(
            actor=owner,
            organization=organization,
            course=revision.course,
            expected_publication_version=publication.lock_version,
            note="Corrección académica necesaria.",
        )
        self.assertEqual(withdrawn.status, PublicationStatus.WITHDRAWN)
        self.assertEqual(withdrawn.current_release_id, release.id)
        same = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=revision,
            expected_publication_version=withdrawn.lock_version,
        )
        same.publication.refresh_from_db()
        self.assertTrue(same.already_released)
        self.assertEqual(same.publication.status, PublicationStatus.WITHDRAWN)
        with self.assertRaises(PublicationTransitionInvalid):
            withdraw_publication(
                actor=owner,
                organization=organization,
                course=revision.course,
                expected_publication_version=withdrawn.lock_version,
                note="Segundo retiro.",
            )

    def test_python_and_postgresql_both_reject_release_mutation_and_delete(
        self,
    ) -> None:
        *_, publication, release = self.published_context()
        release.title = "Alterado"
        with self.assertRaises(ValidationError):
            release.save()
        with self.assertRaises(ValidationError):
            release.delete()
        event = publication.events.first()
        assert event is not None
        event.note = "Alterado"
        with self.assertRaises(ValidationError):
            event.save()
        with transaction.atomic(), self.assertRaises(DatabaseError):
            CourseRelease.objects.filter(pk=release.pk).update(title="Alterado")
        with transaction.atomic(), self.assertRaises(DatabaseError):
            CoursePublicationEvent.objects.filter(pk=event.pk).delete()

    def test_verifier_detects_in_memory_tampering_without_repair(self) -> None:
        *_, release = self.published_context()
        original = deepcopy(release.snapshot)
        release.snapshot["course"]["title"] = "Alterado en memoria"
        result = verify_release(release)
        self.assertFalse(result.valid)
        self.assertIn("digest_mismatch", {issue.code for issue in result.issues})
        self.assertNotEqual(release.snapshot, original)

    def test_create_draft_clones_current_content_and_new_release_reactivates(
        self,
    ) -> None:
        owner, organization, revision, _module, _unit, *_, publication, first = (
            self.published_context()
        )
        withdrawn = withdraw_publication(
            actor=owner,
            organization=organization,
            course=revision.course,
            expected_publication_version=publication.lock_version,
            note="Se prepara una revisión posterior.",
        )
        draft = create_draft_from_release(
            actor=owner,
            organization=organization,
            course=revision.course,
            release_number=first.number,
            expected_publication_version=withdrawn.lock_version,
        )
        self.assertEqual(draft.authoring_status, AuthoringStatus.DRAFT)
        self.assertEqual(draft.based_on_revision_id, revision.id)
        documents = UnitContentDocument.objects.filter(
            unit__module__revision=draft
        ).select_related("current_version")
        self.assertEqual(documents.count(), first.unit_count)
        self.assertTrue(all(document.versions.count() == 1 for document in documents))
        _, draft = confirm_completion_policy(
            actor=owner,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
            require_required_activities=True,
            minimum_grade_basis_points=None,
            minimum_attendance_basis_points=None,
        )
        draft = submit_revision_for_review(
            actor=owner,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
        )
        reviewer = get_user_model().objects.get(
            email="publication-reviewer@example.test"
        )
        draft = approve_revision(
            actor=reviewer,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
        )
        second = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=draft,
            expected_publication_version=withdrawn.lock_version,
        )
        self.assertEqual(second.release.number, 2)
        self.assertEqual(second.release.previous_release_id, first.id)
        self.assertEqual(
            second.release.snapshot["previous_release_digest"],
            first.snapshot_digest,
        )
        self.assertEqual(second.publication.status, PublicationStatus.ACTIVE)
        self.assertTrue(verify_release_chain(revision.course).valid)
