from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.utils import timezone

from domain.catalog.services import assign_subject_teaching_responsibility
from domain.courses.services import (
    approve_revision,
    confirm_completion_policy,
    submit_revision_for_review,
)
from domain.learning.services import enroll_member
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.publishing.services import (
    create_draft_from_release,
    publish_approved_revision,
)
from domain.publishing.tests.support import PublishingFixtureMixin


class LearningFixtureMixin(PublishingFixtureMixin):
    def learning_context(self, *, lesson_kind: str = "document"):
        (
            owner,
            organization,
            revision,
            module,
            unit,
            objective,
            topic,
            publication,
            release,
        ) = self.published_context(lesson_kind=lesson_kind)
        learner = get_user_model().objects.create_user(
            email="learning-learner@example.test",
            password="StrongLearningPassword!42",
        )
        membership = Membership.objects.create(
            organization=organization,
            user=learner,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        enrollment = enroll_member(
            actor=owner,
            organization=organization,
            course=revision.course,
            membership=membership,
            release=release,
        )
        return (
            owner,
            learner,
            organization,
            membership,
            revision,
            module,
            unit,
            publication,
            release,
            enrollment,
        )

    def second_release(self, *, owner, organization, revision, publication, release):
        draft = create_draft_from_release(
            actor=owner,
            organization=organization,
            course=revision.course,
            release_number=release.number,
            expected_publication_version=publication.lock_version,
        )
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
        reviewer = self.member(
            owner,
            organization,
            RoleCode.REVIEWER,
            f"release-reviewer-{revision.id}@example.test",
        )
        assign_subject_teaching_responsibility(
            actor=owner,
            organization=organization,
            subject=draft.subject_alignments.get(position=1).subject,
            membership=Membership.objects.get(organization=organization, user=reviewer),
            starts_on=date(2020, 1, 1),
            ends_on=None,
            rationale="Revisión académica explícita del segundo release.",
        )
        draft = approve_revision(
            actor=reviewer,
            organization=organization,
            revision=draft,
            expected_version=draft.lock_version,
        )
        result = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=draft,
            expected_publication_version=publication.lock_version,
        )
        return result.release
