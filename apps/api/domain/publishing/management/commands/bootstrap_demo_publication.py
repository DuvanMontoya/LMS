# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from domain.courses.choices import AuthoringStatus
from domain.courses.models import Course, CourseRevision
from domain.courses.services import (
    approve_revision,
    confirm_completion_policy,
    submit_revision_for_review,
)
from domain.identity.models import User
from domain.organizations.models import Organization
from domain.publishing.services import publish_approved_revision

DEMO_COURSE_SLUG = "introduccion-calculo-diferencial"


class Command(BaseCommand):
    help = "Aprueba y publica idempotentemente el curso demo sólo en desarrollo."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("La publicación demo sólo se permite con DEBUG=True.")
        organization = Organization.objects.filter(slug="organizacion-demo").first()
        actor = User.objects.filter(email="owner@demo.local").first()
        course = (
            Course.objects.filter(
                organization=organization, slug=DEMO_COURSE_SLUG
            ).first()
            if organization
            else None
        )
        if not organization or not actor or not course:
            raise CommandError(
                "Ejecuta primero los bootstrap demo de organización, currículo, "
                "curso y contenido."
            )
        revision = (
            CourseRevision.objects.filter(course=course).order_by("-number").first()
        )
        if revision is None:
            raise CommandError("El curso demo no tiene una revisión.")
        if (
            revision.authoring_status
            in {AuthoringStatus.DRAFT, AuthoringStatus.CHANGES_REQUESTED}
            and revision.completion_policy.confirmed_at is None
        ):
            _, revision = confirm_completion_policy(
                actor=actor,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                require_required_activities=True,
                minimum_grade_basis_points=None,
                minimum_attendance_basis_points=None,
            )
        if revision.authoring_status in {
            AuthoringStatus.DRAFT,
            AuthoringStatus.CHANGES_REQUESTED,
        }:
            revision = submit_revision_for_review(
                actor=actor,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                note="Preparación determinista del release demo.",
            )
        if revision.authoring_status == AuthoringStatus.IN_REVIEW:
            revision = approve_revision(
                actor=actor,
                organization=organization,
                revision=revision,
                expected_version=revision.lock_version,
                note="Aprobación determinista del release demo.",
            )
        if revision.authoring_status != AuthoringStatus.APPROVED:
            raise CommandError("La revisión demo no está aprobada y no fue modificada.")

        publication = getattr(course, "publication", None)
        result = publish_approved_revision(
            actor=actor,
            organization=organization,
            course=course,
            revision=revision,
            expected_publication_version=(
                publication.lock_version if publication is not None else 0
            ),
        )
        state = "conservado" if result.already_released else "creado"
        self.stdout.write(
            self.style.SUCCESS(
                f"Release demo {state}: {course.slug} v{result.release.number}; "
                f"publicación {result.publication.status}."
            )
        )
