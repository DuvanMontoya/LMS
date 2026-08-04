from __future__ import annotations

from datetime import date

from domain.catalog.services import assign_subject_teaching_responsibility
from domain.content.services import save_unit_content
from domain.content.tests.support import ContentFixtureMixin, full_document
from domain.courses.services import (
    approve_revision,
    configure_mediacms_video_binding,
    confirm_completion_policy,
    replace_unit_topics,
    submit_revision_for_review,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.publishing.services import publish_approved_revision


class PublishingFixtureMixin(ContentFixtureMixin):
    def approved_revision_context(self, *, lesson_kind: str = "document"):
        owner, organization, revision, module, unit, objective, topic = (
            self.unit_context(lesson_kind=lesson_kind)
        )
        revision = replace_unit_topics(
            actor=owner,
            organization=organization,
            unit=unit,
            expected_version=revision.lock_version,
            topics=[topic],
        )
        save_unit_content(
            actor=owner,
            organization=organization,
            revision=revision,
            unit=unit,
            expected_document_version=0,
            schema_version=1,
            content=full_document(),
        )
        if lesson_kind == "mediacms_video":
            _, revision = configure_mediacms_video_binding(
                actor=owner,
                organization=organization,
                unit=unit,
                expected_version=revision.lock_version,
                media_friendly_token="ak7uPO2Vn",
            )
        _, revision = confirm_completion_policy(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            require_required_activities=True,
            minimum_grade_basis_points=None,
            minimum_attendance_basis_points=None,
        )
        revision = submit_revision_for_review(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
        )
        reviewer = self.member(
            owner,
            organization,
            RoleCode.REVIEWER,
            "publication-reviewer@example.test",
        )
        assign_subject_teaching_responsibility(
            actor=owner,
            organization=organization,
            subject=revision.subject_alignments.get(position=1).subject,
            membership=Membership.objects.get(organization=organization, user=reviewer),
            starts_on=date(2020, 1, 1),
            ends_on=None,
            rationale="Revisión académica explícita del fixture.",
        )
        revision = approve_revision(
            actor=reviewer,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
        )
        return owner, organization, revision, module, unit, objective, topic

    def published_context(self, *, lesson_kind: str = "document"):
        context = self.approved_revision_context(lesson_kind=lesson_kind)
        owner, organization, revision, *_ = context
        result = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=revision,
            expected_publication_version=0,
        )
        return (*context, result.publication, result.release)
