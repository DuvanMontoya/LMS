from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from domain.courses.models import Course
from domain.learning.choices import AcademicGroupRole
from domain.learning.exceptions import (
    EnrollmentAlreadyExists,
    EnrollmentConflict,
    LearningProgressConflict,
)
from domain.learning.models import (
    CourseEnrollment,
    EnrollmentCohortAssignment,
    LearningCohort,
    LearningEvent,
    RosterEvent,
)
from domain.learning.services import (
    complete_unit,
    confirm_cohort_roster_sync,
    create_academic_group,
    create_cohort,
    enroll_member,
    open_unit,
    replace_academic_group_roster,
    upgrade_enrollment_release,
)
from domain.organizations.models import Membership, Organization
from domain.publishing.models import CourseRelease

from .support import LearningFixtureMixin


class LearningConcurrencyTests(LearningFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def test_same_progress_version_completes_exactly_once(self) -> None:
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
        expected_version = progress.lock_version
        barrier = threading.Barrier(2)

        def worker() -> str:
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=learner.pk)
                row = CourseEnrollment.objects.get(pk=enrollment.pk)
                barrier.wait(timeout=10)
                complete_unit(
                    actor=actor,
                    enrollment=row,
                    unit_id=unit.id,
                    expected_progress_version=expected_version,
                )
                return "completed"
            except LearningProgressConflict:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: worker(), range(2)))
        self.assertCountEqual(results, ["completed", "conflict"])
        progress.refresh_from_db()
        self.assertEqual(progress.completed_units, 1)
        self.assertEqual(progress.percent_basis_points, 10_000)
        self.assertEqual(
            LearningEvent.objects.filter(
                enrollment=enrollment, event_type="unit_completed"
            ).count(),
            1,
        )

    def test_same_member_is_enrolled_exactly_once(self) -> None:
        (
            owner,
            _learner,
            organization,
            _membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            _enrollment,
        ) = self.learning_context()
        student = get_user_model().objects.create_user(
            email="concurrent-enroll@example.test",
            password="StrongLearningPassword!42",
        )
        membership = Membership.objects.create(
            organization=organization,
            user=student,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        barrier = threading.Barrier(2)

        def worker() -> str:
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                enroll_member(
                    actor=get_user_model().objects.get(pk=owner.pk),
                    organization=Organization.objects.get(pk=organization.pk),
                    course=Course.objects.get(pk=revision.course_id),
                    membership=Membership.objects.get(pk=membership.pk),
                    release=CourseRelease.objects.get(pk=release.pk),
                )
                return "enrolled"
            except EnrollmentAlreadyExists:
                return "duplicate"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: worker(), range(2)))
        self.assertCountEqual(results, ["enrolled", "duplicate"])
        self.assertEqual(
            CourseEnrollment.objects.filter(membership=membership).count(), 1
        )

    def test_same_roster_confirmation_writes_once_and_conflicts_once(self) -> None:
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
            _enrollment,
        ) = self.learning_context()
        group = create_academic_group(
            actor=owner,
            organization=organization,
            name="Grupo concurrente",
            academic_year=2026,
            level="secondary_11",
        )
        group = replace_academic_group_roster(
            actor=owner,
            group=group,
            expected_group_version=group.lock_version,
            members=[
                {
                    "membership_id": membership.id,
                    "role": AcademicGroupRole.LEARNER,
                }
            ],
        )
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            migration_review_required=True,
            academic_group=group,
            name="Curso concurrente",
        )
        expected_cohort_version = cohort.lock_version
        expected_group_version = group.lock_version
        barrier = threading.Barrier(2)

        def worker() -> str:
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                confirm_cohort_roster_sync(
                    actor=get_user_model().objects.get(pk=owner.pk),
                    cohort=LearningCohort.objects.get(pk=cohort.pk),
                    expected_cohort_version=expected_cohort_version,
                    expected_academic_group_version=expected_group_version,
                    reason="Confirmación concurrente",
                )
                return "synced"
            except EnrollmentConflict:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: worker(), range(2)))
        self.assertCountEqual(results, ["synced", "conflict"])
        self.assertEqual(
            EnrollmentCohortAssignment.objects.filter(
                enrollment__membership=membership, ended_at__isnull=True
            ).count(),
            1,
        )
        self.assertEqual(
            RosterEvent.objects.filter(
                cohort=cohort, event_type="course_group_synced"
            ).count(),
            1,
        )

    def test_concurrent_upgrade_uses_enrollment_version(self) -> None:
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
        target = self.second_release(
            owner=owner,
            organization=organization,
            revision=revision,
            publication=publication,
            release=release,
        )
        expected = enrollment.lock_version
        barrier = threading.Barrier(2)

        def worker() -> str:
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                upgrade_enrollment_release(
                    actor=get_user_model().objects.get(pk=owner.pk),
                    enrollment=CourseEnrollment.objects.get(pk=enrollment.pk),
                    expected_enrollment_version=expected,
                    target_release=CourseRelease.objects.get(pk=target.pk),
                )
                return "upgraded"
            except EnrollmentConflict:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: worker(), range(2)))
        self.assertCountEqual(results, ["upgraded", "conflict"])
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.current_release_assignment.release_id, target.id)
        self.assertEqual(enrollment.release_assignments.count(), 2)
