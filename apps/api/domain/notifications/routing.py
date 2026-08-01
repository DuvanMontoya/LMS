# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from dataclasses import dataclass

from domain.events.models import DomainEvent

from .models import NotificationCategory


@dataclass(frozen=True)
class NotificationRoute:
    recipient_ids: tuple[object, ...]
    category: str
    template_key: str
    title: str
    body: str
    action_url: str


def _enrollment_route(event: DomainEvent, action: str) -> NotificationRoute:
    from domain.learning.models import CourseEnrollment

    enrollment = CourseEnrollment.objects.select_related(
        "membership__user", "course"
    ).get(pk=event.payload["enrollment_id"])
    labels = {
        "created": ("Matrícula creada", "Ya tienes acceso a un nuevo curso."),
        "suspended": ("Acceso suspendido", "Tu acceso al curso fue suspendido."),
        "reactivated": ("Acceso reactivado", "Tu acceso al curso fue reactivado."),
        "revoked": ("Acceso revocado", "Tu matrícula fue revocada."),
    }
    title, body = labels[action]
    return NotificationRoute(
        (enrollment.membership.user_id,),
        NotificationCategory.LEARNING,
        f"enrollment_{action}",
        title,
        body,
        f"/organizaciones/{enrollment.organization.slug}/aprendizaje",
    )


def _attempt_route(event: DomainEvent, pending: bool) -> NotificationRoute:
    from domain.assessments.models import Attempt

    attempt = Attempt.objects.select_related(
        "delivery_assignment__release_assignment__enrollment__membership__user",
        "delivery_assignment__delivery__organization",
    ).get(pk=event.payload["attempt_id"])
    enrollment = attempt.delivery_assignment.release_assignment.enrollment
    organization = attempt.delivery_assignment.delivery.organization
    return NotificationRoute(
        (enrollment.membership.user_id,),
        NotificationCategory.ASSESSMENT,
        "assessment_pending_manual" if pending else "assessment_graded",
        "Evaluación pendiente de revisión" if pending else "Evaluación calificada",
        "Tu entrega requiere revisión manual."
        if pending
        else "Tu calificación ya está disponible.",
        f"/organizaciones/{organization.slug}/evaluaciones/intentos/{attempt.id}/resultado",
    )


def _asset_route(event: DomainEvent, action: str) -> NotificationRoute:
    from domain.assets.models import AssetVersion

    version = AssetVersion.objects.select_related(
        "asset__organization", "created_by"
    ).get(pk=event.payload["asset_version_id"])
    title = {
        "ready": "Recurso listo",
        "rejected": "Recurso rechazado",
        "failed": "Procesamiento fallido",
    }[action]
    return NotificationRoute(
        (version.created_by_id,),
        NotificationCategory.ASSET,
        f"asset_{action}",
        title,
        "Consulta el estado y los detalles del recurso.",
        f"/organizaciones/{version.asset.organization.slug}/recursos/{version.asset_id}",
    )


def _course_revision_route(event: DomainEvent) -> NotificationRoute:
    from domain.courses.models import CourseRevision

    revision = CourseRevision.objects.select_related(
        "course__organization", "created_by"
    ).get(pk=event.payload["revision_id"])
    return NotificationRoute(
        (revision.created_by_id,),
        NotificationCategory.AUTHORING,
        "course_revision_changes_requested",
        "Cambios solicitados en el curso",
        "La revisión requiere ajustes antes de volver a enviarse.",
        f"/organizaciones/{revision.course.organization.slug}/cursos/{revision.course.slug}",
    )


def _assessment_revision_route(
    event: DomainEvent, *, question: bool
) -> NotificationRoute:
    if question:
        from domain.assessments.models import QuestionRevision

        revision = QuestionRevision.objects.select_related(
            "question__bank__organization", "created_by"
        ).get(pk=event.payload["question_revision_id"])
        return NotificationRoute(
            (revision.created_by_id,),
            NotificationCategory.AUTHORING,
            "question_revision_changes_requested",
            "Cambios solicitados en la pregunta",
            "La revisión de pregunta requiere ajustes.",
            f"/organizaciones/{revision.question.bank.organization.slug}/evaluaciones/bancos/{revision.question.bank_id}",
        )
    from domain.assessments.models import AssessmentRevision

    revision = AssessmentRevision.objects.select_related(
        "assessment__organization", "created_by"
    ).get(pk=event.payload["assessment_revision_id"])
    return NotificationRoute(
        (revision.created_by_id,),
        NotificationCategory.AUTHORING,
        "assessment_revision_changes_requested",
        "Cambios solicitados en la evaluación",
        "La revisión de evaluación requiere ajustes.",
        f"/organizaciones/{revision.assessment.organization.slug}/evaluaciones/{revision.assessment.slug}",
    )


def _publication_route(event: DomainEvent, *, withdrawn: bool) -> NotificationRoute:
    if withdrawn:
        from domain.learning.choices import EnrollmentStatus
        from domain.learning.models import CourseEnrollment
        from domain.publishing.models import CoursePublication

        publication = CoursePublication.objects.select_related(
            "course__organization"
        ).get(pk=event.payload["course_publication_id"])
        recipients = tuple(
            CourseEnrollment.objects.filter(
                course=publication.course, status=EnrollmentStatus.ACTIVE
            )
            .values_list("membership__user_id", flat=True)
            .distinct()[:10_001]
        )
        return NotificationRoute(
            recipients,
            NotificationCategory.PUBLICATION,
            "publication_withdrawn",
            "Curso retirado",
            "El curso fue retirado de la biblioteca.",
            f"/organizaciones/{publication.course.organization.slug}/aprendizaje",
        )
    from domain.publishing.models import CourseRelease

    release = CourseRelease.objects.select_related(
        "course__organization", "course__created_by"
    ).get(pk=event.payload["course_release_id"])
    return NotificationRoute(
        (release.course.created_by_id,),
        NotificationCategory.PUBLICATION,
        "course_published",
        "Curso publicado",
        "Una nueva versión del curso está disponible.",
        f"/organizaciones/{release.course.organization.slug}/cursos/{release.course.slug}/publicacion",
    )


def _regrade_route(event: DomainEvent) -> NotificationRoute:
    from domain.assessments.models import RegradeJob

    job = RegradeJob.objects.select_related("organization", "created_by").get(
        pk=event.payload["regrade_id"]
    )
    return NotificationRoute(
        (job.created_by_id,),
        NotificationCategory.ASSESSMENT,
        "regrade_completed",
        "Recalificación completada",
        "El proceso de recalificación terminó; revisa sus resultados.",
        f"/organizaciones/{job.organization.slug}/evaluaciones/regrading/{job.id}",
    )


def route_event(event: DomainEvent) -> NotificationRoute | None:
    parts = event.event_type.split(".")
    action = parts[2]
    if event.event_type.startswith("learning.enrollment."):
        return _enrollment_route(event, action)
    if event.event_type == "assessments.attempt.graded.v1":
        return _attempt_route(event, False)
    if event.event_type == "assessments.attempt.pending_manual.v1":
        return _attempt_route(event, True)
    if event.event_type.startswith("assets.asset_version."):
        return _asset_route(event, action)
    if event.event_type == "courses.revision.changes_requested.v1":
        return _course_revision_route(event)
    if event.event_type == "assessments.question_revision.changes_requested.v1":
        return _assessment_revision_route(event, question=True)
    if event.event_type == "assessments.assessment_revision.changes_requested.v1":
        return _assessment_revision_route(event, question=False)
    if event.event_type == "publishing.course_release.published.v1":
        return _publication_route(event, withdrawn=False)
    if event.event_type == "publishing.course_publication.withdrawn.v1":
        return _publication_route(event, withdrawn=True)
    if event.event_type == "assessments.regrade.completed.v1":
        return _regrade_route(event)
    return None
