from __future__ import annotations

from domain.content.services import save_unit_content
from domain.content.tests.support import ContentFixtureMixin, full_document
from domain.courses.services import (
    approve_revision,
    replace_unit_topics,
    submit_revision_for_review,
)
from domain.publishing.services import publish_approved_revision


class PublishingFixtureMixin(ContentFixtureMixin):
    def approved_revision_context(self):
        owner, organization, revision, module, unit, objective, topic = (
            self.unit_context()
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
        revision = submit_revision_for_review(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
        )
        revision = approve_revision(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
        )
        return owner, organization, revision, module, unit, objective, topic

    def published_context(self):
        context = self.approved_revision_context()
        owner, organization, revision, *_ = context
        result = publish_approved_revision(
            actor=owner,
            organization=organization,
            course=revision.course,
            revision=revision,
            expected_publication_version=0,
        )
        return (*context, result.publication, result.release)
