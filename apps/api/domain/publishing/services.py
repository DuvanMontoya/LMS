# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from domain.content.exceptions import ContentDomainError
from domain.content.services import (
    clone_current_unit_documents,
    clone_current_unit_lesson_resources,
)
from domain.courses.choices import AuthoringStatus, CourseStatus
from domain.courses.exceptions import (
    CourseAccessDenied,
    CourseRevisionAlreadyOpen,
    CourseRevisionTransitionInvalid,
)
from domain.courses.models import Course, CourseRevision
from domain.courses.readiness import revision_readiness_issues
from domain.courses.services import clone_approved_revision_structure
from domain.events.services import record_domain_event
from domain.organizations.models import Organization

from .choices import PublicationEventType, PublicationStatus
from .exceptions import (
    DraftAlreadyOpen,
    DraftCreationInvalid,
    PublicationAccessDenied,
    PublicationConflict,
    PublicationTransitionInvalid,
    ReleaseChainInvalid,
    ReleaseSnapshotInvalid,
    ReleaseSourceNotApproved,
    ReleaseSourceNotNewer,
    WithdrawalNoteRequired,
)
from .integrity import verify_release, verify_release_chain
from .limits import MAX_WITHDRAWAL_NOTE_LENGTH
from .models import CoursePublication, CoursePublicationEvent, CourseRelease
from .policies import can_create_draft, can_publish, can_withdraw
from .snapshots import (
    build_release_snapshot,
    load_release_revision,
    snapshot_metrics,
)


@dataclass(frozen=True)
class PublishResult:
    publication: CoursePublication
    release: CourseRelease
    already_released: bool
    is_current: bool


def _require(condition: bool, error: type[Exception], message: str) -> None:
    if not condition:
        raise error(message)


def _check_expected(
    publication: CoursePublication | None, expected_publication_version: int
) -> None:
    current = publication.lock_version if publication else 0
    if current != expected_publication_version:
        raise PublicationConflict(
            "La publicación cambió desde que abriste esta pantalla."
        )


@transaction.atomic
def publish_approved_revision(
    *,
    actor: Any,
    organization: Organization,
    course: Course,
    revision: CourseRevision,
    expected_publication_version: int,
) -> PublishResult:
    locked_course = (
        Course.objects.select_for_update()
        .select_related("organization")
        .get(pk=course.pk)
    )
    _require(
        locked_course.organization_id == organization.id,
        PublicationAccessDenied,
        "El curso no pertenece a la organización.",
    )
    _require(
        can_publish(actor, organization),
        PublicationAccessDenied,
        "No tienes capacidad para publicar.",
    )
    _require(
        locked_course.status == CourseStatus.ACTIVE,
        ReleaseSourceNotApproved,
        "El curso debe estar activo.",
    )
    locked_revision = CourseRevision.objects.select_for_update().get(pk=revision.pk)
    _require(
        locked_revision.course_id == locked_course.id
        and locked_revision.authoring_status == AuthoringStatus.APPROVED,
        ReleaseSourceNotApproved,
        "La revisión fuente no está aprobada.",
    )
    publication = (
        CoursePublication.objects.select_for_update()
        .select_related("current_release__source_revision")
        .filter(course=locked_course)
        .first()
    )
    _check_expected(publication, expected_publication_version)
    existing = (
        CourseRelease.objects.filter(source_revision=locked_revision)
        .select_related("course")
        .first()
    )
    if existing is not None:
        _require(
            existing.course_id == locked_course.id,
            ReleaseChainInvalid,
            "El release existente pertenece a otro curso.",
        )
        assert publication is not None
        return PublishResult(
            publication,
            existing,
            already_released=True,
            is_current=publication.current_release_id == existing.id,
        )
    previous = publication.current_release if publication else None
    if previous is not None:
        chain = verify_release_chain(locked_course)
        _require(
            chain.valid,
            ReleaseChainInvalid,
            "La cadena existente no supera la verificación.",
        )
        _require(
            locked_revision.number > previous.source_revision.number,
            ReleaseSourceNotNewer,
            "La revisión fuente no es posterior al release vigente.",
        )
    issues = revision_readiness_issues(locked_revision)
    if issues:
        raise ReleaseSnapshotInvalid(
            "La revisión no está lista para publicarse: "
            + ", ".join(issue["code"] for issue in issues[:10])
        )
    hydrated_revision = load_release_revision(locked_revision)
    number = previous.number + 1 if previous else 1
    snapshot, canonical = build_release_snapshot(
        revision=hydrated_revision,
        release_number=number,
        previous_release_digest=previous.snapshot_digest if previous else None,
    )
    metrics = snapshot_metrics(snapshot)
    now = timezone.now()
    release = CourseRelease.objects.create(
        course=locked_course,
        number=number,
        source_revision=locked_revision,
        previous_release=previous,
        schema_version=snapshot["schema_version"],
        snapshot=snapshot,
        snapshot_digest=hashlib.sha256(canonical).hexdigest(),
        snapshot_size_bytes=len(canonical),
        title=snapshot["course"]["title"],
        summary=snapshot["course"]["summary"],
        language_code=snapshot["course"]["language_code"],
        estimated_duration_minutes=snapshot["course"]["estimated_duration_minutes"],
        module_count=metrics["module_count"],
        unit_count=metrics["unit_count"],
        word_count=metrics["word_count"],
        created_by=actor,
    )
    if publication is None:
        publication = CoursePublication.objects.create(
            course=locked_course,
            current_release=release,
            status=PublicationStatus.ACTIVE,
            lock_version=1,
            first_published_at=now,
            first_published_by=actor,
            last_published_at=now,
            last_published_by=actor,
        )
    else:
        publication.current_release = release
        publication.status = PublicationStatus.ACTIVE
        publication.last_published_at = now
        publication.last_published_by = actor
        publication.withdrawn_at = None
        publication.withdrawn_by = None
        publication.withdrawal_note = ""
        publication.lock_version += 1
        publication.save(
            update_fields=[
                "current_release",
                "status",
                "last_published_at",
                "last_published_by",
                "withdrawn_at",
                "withdrawn_by",
                "withdrawal_note",
                "lock_version",
                "updated_at",
            ]
        )
    CoursePublicationEvent.objects.create(
        course=locked_course,
        publication=publication,
        release=release,
        revision=locked_revision,
        event_type=PublicationEventType.RELEASE_PUBLISHED,
        actor=actor,
    )
    record_domain_event(
        event_type="publishing.course_release.published.v1",
        organization=organization,
        aggregate_type="course_release",
        aggregate_id=release.id,
        actor=actor,
        payload={
            "course_release_id": str(release.id),
            "course_id": str(locked_course.id),
            "release_id": str(release.id),
        },
    )
    return PublishResult(publication, release, False, True)


@transaction.atomic
def withdraw_publication(
    *,
    actor: Any,
    organization: Organization,
    course: Course,
    expected_publication_version: int,
    note: str,
) -> CoursePublication:
    locked_course = Course.objects.select_for_update().get(pk=course.pk)
    _require(
        locked_course.organization_id == organization.id,
        PublicationAccessDenied,
        "El curso no pertenece a la organización.",
    )
    _require(
        can_withdraw(actor, organization),
        PublicationAccessDenied,
        "No tienes capacidad para retirar.",
    )
    publication = (
        CoursePublication.objects.select_for_update()
        .select_related("current_release")
        .filter(course=locked_course)
        .first()
    )
    _require(
        publication is not None,
        PublicationTransitionInvalid,
        "El curso no tiene una publicación.",
    )
    assert publication is not None
    _check_expected(publication, expected_publication_version)
    _require(
        publication.status == PublicationStatus.ACTIVE,
        PublicationTransitionInvalid,
        "La publicación ya está retirada.",
    )
    cleaned_note = note.strip()
    if not cleaned_note:
        raise WithdrawalNoteRequired("La justificación de retiro es obligatoria.")
    if len(cleaned_note) > MAX_WITHDRAWAL_NOTE_LENGTH:
        raise WithdrawalNoteRequired("La justificación de retiro es demasiado larga.")
    publication.status = PublicationStatus.WITHDRAWN
    publication.withdrawn_at = timezone.now()
    publication.withdrawn_by = actor
    publication.withdrawal_note = cleaned_note
    publication.lock_version += 1
    publication.save(
        update_fields=[
            "status",
            "withdrawn_at",
            "withdrawn_by",
            "withdrawal_note",
            "lock_version",
            "updated_at",
        ]
    )
    CoursePublicationEvent.objects.create(
        course=locked_course,
        publication=publication,
        release=publication.current_release,
        event_type=PublicationEventType.PUBLICATION_WITHDRAWN,
        actor=actor,
        note=cleaned_note,
    )
    record_domain_event(
        event_type="publishing.course_publication.withdrawn.v1",
        organization=organization,
        aggregate_type="course_publication",
        aggregate_id=publication.id,
        actor=actor,
        payload={
            "course_publication_id": str(publication.id),
            "course_id": str(locked_course.id),
            "release_id": str(publication.current_release_id),
        },
    )
    return publication


@transaction.atomic
def create_draft_from_release(
    *,
    actor: Any,
    organization: Organization,
    course: Course,
    release_number: int,
    expected_publication_version: int,
) -> CourseRevision:
    locked_course = Course.objects.select_for_update().get(pk=course.pk)
    _require(
        locked_course.organization_id == organization.id,
        PublicationAccessDenied,
        "El curso no pertenece a la organización.",
    )
    _require(
        can_create_draft(actor, organization),
        PublicationAccessDenied,
        "No tienes capacidad para crear un draft.",
    )
    publication = (
        CoursePublication.objects.select_for_update()
        .filter(course=locked_course)
        .first()
    )
    _require(
        publication is not None,
        PublicationTransitionInvalid,
        "El curso no tiene una publicación.",
    )
    assert publication is not None
    _check_expected(publication, expected_publication_version)
    release = (
        CourseRelease.objects.select_related("source_revision")
        .filter(course=locked_course, number=release_number)
        .first()
    )
    _require(release is not None, DraftCreationInvalid, "El release no existe.")
    assert release is not None
    _require(
        verify_release(release).valid,
        ReleaseChainInvalid,
        "El release no supera la verificación.",
    )
    try:
        clone = clone_approved_revision_structure(
            actor=actor, source_revision=release.source_revision
        )
        clone_current_unit_documents(
            actor=actor, units_by_source_id=clone.units_by_source_id
        )
        clone_current_unit_lesson_resources(
            actor=actor, units_by_source_id=clone.units_by_source_id
        )
    except CourseRevisionAlreadyOpen as error:
        raise DraftAlreadyOpen("El curso ya tiene una revisión abierta.") from error
    except (
        CourseAccessDenied,
        CourseRevisionTransitionInvalid,
        ContentDomainError,
    ) as error:
        raise DraftCreationInvalid("No fue posible clonar el release.") from error
    CoursePublicationEvent.objects.create(
        course=locked_course,
        publication=publication,
        release=release,
        revision=clone.revision,
        event_type=PublicationEventType.DRAFT_CREATED_FROM_RELEASE,
        actor=actor,
    )
    return clone.revision
