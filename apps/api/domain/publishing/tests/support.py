from __future__ import annotations

from datetime import date

from domain.assets.choices import AssetKind, AssetVersionStatus, VariantRole
from domain.assets.models import Asset, AssetVariant, AssetVersion
from domain.catalog.services import assign_subject_teaching_responsibility
from domain.content.services import configure_unit_lesson_resource, save_unit_content
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
    def ready_delivery_asset(
        self, *, owner, organization, lesson_kind: str
    ) -> AssetVersion:
        metadata = {
            "latex_source": (AssetKind.DOCUMENT, "source.tex", "application/x-tex"),
            "markdown_source": (AssetKind.DOCUMENT, "source.md", "text/markdown"),
            "pdf": (AssetKind.DOCUMENT, "lesson.pdf", "application/pdf"),
            "slides": (
                AssetKind.DOCUMENT,
                "slides.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            "audio": (AssetKind.AUDIO, "lesson.mp3", "audio/mpeg"),
        }
        kind, filename, mime_type = metadata[lesson_kind]
        asset = Asset.objects.create(
            organization=organization,
            kind=kind,
            name=f"Delivery {lesson_kind}",
            created_by=owner,
            updated_by=owner,
        )
        version = AssetVersion.objects.create(
            asset=asset,
            number=1,
            status=AssetVersionStatus.READY,
            original_filename=filename,
            declared_mime_type=mime_type,
            detected_mime_type=mime_type,
            extension=f".{filename.rsplit('.', maxsplit=1)[1]}",
            size_bytes=10,
            sha256="a" * 64,
            storage_bucket="private",
            storage_key=f"originals/{filename}",
            expected_asset_lock_version=1,
            created_by=owner,
        )
        if kind == AssetKind.AUDIO:
            AssetVariant.objects.create(
                asset_version=version,
                role=VariantRole.AUDIO_PLAYBACK,
                pipeline_name="media",
                pipeline_version="1",
                mime_type="audio/mpeg",
                extension=".mp3",
                storage_bucket="private",
                storage_key="variants/lesson.mp3",
                size_bytes=10,
                sha256="b" * 64,
            )
        asset.current_version = version
        asset.save(update_fields=["current_version", "updated_at"])
        return version

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
        if lesson_kind == "document":
            save_unit_content(
                actor=owner,
                organization=organization,
                revision=revision,
                unit=unit,
                expected_document_version=0,
                schema_version=1,
                content=full_document(),
            )
        elif lesson_kind == "mediacms_video":
            _, revision = configure_mediacms_video_binding(
                actor=owner,
                organization=organization,
                unit=unit,
                expected_version=revision.lock_version,
                media_friendly_token="ak7uPO2Vn",
            )
        else:
            version = self.ready_delivery_asset(
                owner=owner,
                organization=organization,
                lesson_kind=lesson_kind,
            )
            _, revision = configure_unit_lesson_resource(
                actor=owner,
                organization=organization,
                revision=revision,
                unit=unit,
                expected_version=revision.lock_version,
                asset_version_id=version.id,
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
