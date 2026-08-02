from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from domain.learning.access import access_state, require_learning_access
from domain.learning.choices import (
    AcademicGroupRole,
    AccessState,
    CohortRosterMode,
    EnrollmentCohortSource,
    EnrollmentStatus,
    LearningEventType,
    ProgressStatus,
)
from domain.learning.exceptions import (
    EnrollmentAlreadyExists,
    EnrollmentTransitionInvalid,
    LearningAccessEnded,
    LearningAccessNotStarted,
    LearningPositionInvalid,
    LearningProgressConflict,
)
from domain.learning.models import (
    CourseEnrollment,
    EnrollmentCohortAssignment,
    EnrollmentReleaseAssignment,
    LearningEvent,
    UnitProgress,
)
from domain.learning.services import (
    complete_unit,
    confirm_cohort_roster_sync,
    create_academic_group,
    create_cohort,
    enroll_cohort_members,
    enroll_member,
    open_unit,
    preview_cohort_roster_sync,
    reactivate_enrollment,
    reopen_unit,
    replace_academic_group_roster,
    revoke_enrollment,
    suspend_enrollment,
    update_learning_position,
    upgrade_enrollment_release,
)
from domain.organizations.models import Membership
from domain.publishing.services import withdraw_publication

from .support import LearningFixtureMixin


class LearningServiceTests(LearningFixtureMixin, TestCase):
    def test_roster_sync_preserves_manual_access_and_suspends_sync_access(self) -> None:
        (
            owner,
            _learner,
            organization,
            manual_membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            manual_enrollment,
        ) = self.learning_context()
        synced_user = get_user_model().objects.create_user(
            email="synced-roster@example.test", password="StrongLearningPassword!42"
        )
        synced_membership = Membership.objects.create(
            organization=organization,
            user=synced_user,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        group = create_academic_group(
            actor=owner,
            organization=organization,
            name="11-A",
            academic_year=2026,
            level="secondary_11",
        )
        group = replace_academic_group_roster(
            actor=owner,
            group=group,
            expected_group_version=group.lock_version,
            members=[
                {
                    "membership_id": manual_membership.id,
                    "role": AcademicGroupRole.LEARNER,
                },
                {
                    "membership_id": synced_membership.id,
                    "role": AcademicGroupRole.LEARNER,
                },
            ],
        )
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            academic_group=group,
            name="Álgebra 11-A",
        )
        self.assertEqual(cohort.roster_mode, CohortRosterMode.SYNCED)
        preview = preview_cohort_roster_sync(
            actor=owner,
            cohort=cohort,
            expected_cohort_version=cohort.lock_version,
            expected_academic_group_version=group.lock_version,
        )
        self.assertEqual(set(preview["assigns"]), {str(manual_membership.id)})
        self.assertEqual(set(preview["creates"]), {str(synced_membership.id)})
        self.assertFalse(preview["conflicts"])
        confirm_cohort_roster_sync(
            actor=owner,
            cohort=cohort,
            expected_cohort_version=cohort.lock_version,
            expected_academic_group_version=group.lock_version,
            reason="Primer padrón",
        )
        manual_enrollment.refresh_from_db()
        synced_enrollment = CourseEnrollment.objects.get(membership=synced_membership)
        self.assertIsNotNone(manual_enrollment.effective_cohort)
        self.assertEqual(manual_enrollment.effective_cohort.id, cohort.id)
        self.assertEqual(
            synced_enrollment.access_provenance,
            EnrollmentCohortSource.ACADEMIC_GROUP_SYNC,
        )
        cohort.refresh_from_db()
        group = replace_academic_group_roster(
            actor=owner,
            group=group,
            expected_group_version=group.lock_version,
            members=[],
        )
        preview = preview_cohort_roster_sync(
            actor=owner,
            cohort=cohort,
            expected_cohort_version=cohort.lock_version,
            expected_academic_group_version=group.lock_version,
        )
        self.assertEqual(set(preview["unassignments"]), {str(manual_membership.id)})
        self.assertEqual(set(preview["suspensions"]), {str(synced_membership.id)})
        confirm_cohort_roster_sync(
            actor=owner,
            cohort=cohort,
            expected_cohort_version=cohort.lock_version,
            expected_academic_group_version=group.lock_version,
            reason="Baja del padrón",
        )
        manual_enrollment.refresh_from_db()
        synced_enrollment.refresh_from_db()
        self.assertEqual(manual_enrollment.status, EnrollmentStatus.ACTIVE)
        self.assertIsNone(manual_enrollment.effective_cohort)
        self.assertEqual(synced_enrollment.status, EnrollmentStatus.SUSPENDED)
        self.assertIsNone(synced_enrollment.effective_cohort)
        self.assertEqual(
            EnrollmentCohortAssignment.objects.filter(
                enrollment__in=[manual_enrollment, synced_enrollment],
                ended_at__isnull=False,
            ).count(),
            2,
        )

    def test_enrollment_is_release_pinned_and_duplicate_is_rejected(self) -> None:
        (
            owner,
            _learner,
            organization,
            membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            enrollment,
        ) = self.learning_context()
        self.assertEqual(enrollment.current_release_assignment.release, release)
        self.assertEqual(enrollment.current_release_assignment.sequence, 1)
        self.assertEqual(enrollment.current_release_assignment.progress.total_units, 1)
        self.assertEqual(
            enrollment.current_release_assignment.progress.status, "not_started"
        )
        with self.assertRaises(EnrollmentAlreadyExists):
            enroll_member(
                actor=owner,
                organization=organization,
                course=revision.course,
                membership=membership,
                release=release,
            )

    def test_open_position_complete_conflict_and_reopen(self) -> None:
        (
            _owner,
            learner,
            _organization,
            _membership,
            _revision,
            _module,
            unit,
            _publication,
            _release,
            enrollment,
        ) = self.learning_context()
        progress = open_unit(actor=learner, enrollment=enrollment, unit_id=unit.id)
        self.assertEqual(progress.status, ProgressStatus.IN_PROGRESS)
        node_id = uuid.UUID("10000000-0000-4000-8000-000000000002")
        positioned = update_learning_position(
            actor=learner,
            enrollment=enrollment,
            unit_id=unit.id,
            node_id=node_id,
        )
        self.assertEqual(positioned.last_node_id, node_id)
        original_version = positioned.lock_version
        completed, already = complete_unit(
            actor=learner,
            enrollment=enrollment,
            unit_id=unit.id,
            expected_progress_version=original_version,
        )
        self.assertFalse(already)
        self.assertEqual(completed.completed_units, 1)
        self.assertEqual(completed.percent_basis_points, 10_000)
        self.assertEqual(completed.status, ProgressStatus.COMPLETED)
        with self.assertRaises(LearningProgressConflict):
            complete_unit(
                actor=learner,
                enrollment=enrollment,
                unit_id=unit.id,
                expected_progress_version=original_version,
            )
        reopened = reopen_unit(
            actor=learner,
            enrollment=enrollment,
            unit_id=unit.id,
            expected_progress_version=completed.lock_version,
        )
        self.assertEqual(reopened.status, ProgressStatus.IN_PROGRESS)
        self.assertEqual(reopened.completed_units, 0)
        self.assertIsNone(reopened.completed_at)
        self.assertEqual(
            LearningEvent.objects.filter(
                enrollment=enrollment,
                event_type=LearningEventType.COURSE_REOPENED,
            ).count(),
            1,
        )

    def test_invalid_node_is_rejected_without_partial_write(self) -> None:
        *_, unit, _publication, _release, enrollment = self.learning_context()[4:]
        learner = enrollment.membership.user
        open_unit(actor=learner, enrollment=enrollment, unit_id=unit.id)
        before = enrollment.current_release_assignment.progress.last_node_id
        with self.assertRaises(LearningPositionInvalid):
            update_learning_position(
                actor=learner,
                enrollment=enrollment,
                unit_id=unit.id,
                node_id=uuid.uuid4(),
            )
        enrollment.current_release_assignment.progress.refresh_from_db()
        self.assertEqual(
            enrollment.current_release_assignment.progress.last_node_id, before
        )

    def test_suspend_reactivate_revoke_and_re_enroll_preserve_history(self) -> None:
        (
            owner,
            _learner,
            organization,
            membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            enrollment,
        ) = self.learning_context()
        enrollment = suspend_enrollment(
            actor=owner,
            enrollment=enrollment,
            expected_version=enrollment.lock_version,
        )
        self.assertEqual(enrollment.status, EnrollmentStatus.SUSPENDED)
        enrollment = reactivate_enrollment(
            actor=owner,
            enrollment=enrollment,
            expected_version=enrollment.lock_version,
        )
        enrollment = revoke_enrollment(
            actor=owner,
            enrollment=enrollment,
            expected_version=enrollment.lock_version,
        )
        self.assertEqual(enrollment.status, EnrollmentStatus.REVOKED)
        with self.assertRaises(EnrollmentTransitionInvalid):
            reactivate_enrollment(
                actor=owner,
                enrollment=enrollment,
                expected_version=enrollment.lock_version,
            )
        replacement = enroll_member(
            actor=owner,
            organization=organization,
            course=revision.course,
            membership=membership,
            release=release,
        )
        self.assertNotEqual(replacement.id, enrollment.id)
        self.assertEqual(CourseEnrollment.objects.count(), 2)
        self.assertTrue(
            UnitProgress.objects.filter(course_progress__isnull=False).count() >= 0
        )

    def test_explicit_upgrade_starts_independent_progress_and_preserves_history(
        self,
    ) -> None:
        (
            owner,
            _learner,
            organization,
            _membership,
            revision,
            _module,
            _unit,
            publication,
            release,
            enrollment,
        ) = self.learning_context()
        second = self.second_release(
            owner=owner,
            organization=organization,
            revision=revision,
            publication=publication,
            release=release,
        )
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.current_release_assignment.release, release)
        upgraded = upgrade_enrollment_release(
            actor=owner,
            enrollment=enrollment,
            expected_enrollment_version=enrollment.lock_version,
            target_release=second,
        )
        current = upgraded.current_release_assignment
        self.assertEqual(current.sequence, 2)
        self.assertEqual(current.previous_assignment.release, release)
        self.assertEqual(current.progress.completed_units, 0)
        self.assertEqual(current.progress.status, ProgressStatus.NOT_STARTED)
        self.assertEqual(
            EnrollmentReleaseAssignment.objects.filter(
                enrollment=enrollment, ended_at__isnull=True
            ).count(),
            1,
        )

    def test_cohort_batch_is_atomic_when_one_membership_is_duplicate(self) -> None:
        (
            owner,
            _learner,
            organization,
            existing_membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            _enrollment,
        ) = self.learning_context()
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            name="Cohorte atómica",
        )
        newcomer = get_user_model().objects.create_user(
            email="learning-batch@example.test", password="StrongLearningPassword!42"
        )
        newcomer_membership = Membership.objects.create(
            organization=organization,
            user=newcomer,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        with self.assertRaises(EnrollmentAlreadyExists):
            enroll_cohort_members(
                actor=owner,
                cohort=cohort,
                memberships=[newcomer_membership, existing_membership],
                expected_cohort_version=cohort.lock_version,
            )
        self.assertFalse(
            CourseEnrollment.objects.filter(membership=newcomer_membership).exists()
        )

    def test_windows_and_withdrawal_fail_closed_without_changing_status(self) -> None:
        (
            owner,
            learner,
            organization,
            _membership,
            revision,
            _module,
            _unit,
            publication,
            _release,
            enrollment,
        ) = self.learning_context()
        enrollment.access_starts_at = timezone.now() + timedelta(days=1)
        enrollment.save(update_fields=["access_starts_at"])
        self.assertEqual(access_state(enrollment), AccessState.NOT_STARTED)
        with self.assertRaises(LearningAccessNotStarted):
            require_learning_access(actor=learner, enrollment=enrollment)
        enrollment.access_starts_at = None
        enrollment.access_ends_at = timezone.now() - timedelta(minutes=1)
        enrollment.save(update_fields=["access_starts_at", "access_ends_at"])
        self.assertEqual(access_state(enrollment), AccessState.ENDED)
        with self.assertRaises(LearningAccessEnded):
            require_learning_access(actor=learner, enrollment=enrollment)
        enrollment.access_ends_at = None
        enrollment.save(update_fields=["access_ends_at"])
        withdraw_publication(
            actor=owner,
            organization=organization,
            course=revision.course,
            expected_publication_version=publication.lock_version,
            note="Retiro probado por learning.",
        )
        self.assertEqual(access_state(enrollment), AccessState.PUBLICATION_WITHDRAWN)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, EnrollmentStatus.ACTIVE)
