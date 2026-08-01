# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from domain.discovery.models import GenerationStatus, SearchGeneration
from domain.discovery.services import rebuild_search_index
from domain.events.models import DomainEvent
from domain.learning.choices import EnrollmentStatus
from domain.learning.models import CourseEnrollment
from domain.learning.services import reactivate_enrollment, suspend_enrollment
from domain.notifications.models import Notification, NotificationCategory
from domain.organizations.models import Organization


class Command(BaseCommand):
    help = "Construye búsqueda y una notificación controlada para el demo local."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError(
                "El demo de operaciones de plataforma sólo se permite con DEBUG=True."
            )
        organization = Organization.objects.filter(slug="organizacion-demo").first()
        recipient = get_user_model().objects.filter(email="learner@demo.local").first()
        if organization is None or recipient is None:
            raise CommandError("Ejecuta primero los demos académicos existentes.")
        event = (
            DomainEvent.objects.filter(organization=organization)
            .order_by("created_at", "id")
            .first()
        )
        if event is None:
            actor = get_user_model().objects.filter(email="owner@demo.local").first()
            enrollment = (
                CourseEnrollment.objects.select_related("membership__user")
                .filter(
                    organization=organization,
                    membership__user=recipient,
                    status=EnrollmentStatus.ACTIVE,
                )
                .first()
            )
            if actor is None or enrollment is None:
                raise CommandError("Ejecuta primero los demos académicos existentes.")
            suspended = suspend_enrollment(
                actor=actor,
                enrollment=enrollment,
                expected_version=enrollment.lock_version,
            )
            reactivate_enrollment(
                actor=actor,
                enrollment=suspended,
                expected_version=suspended.lock_version,
            )
            event = (
                DomainEvent.objects.filter(organization=organization)
                .order_by("created_at", "id")
                .first()
            )
            if event is None:
                raise CommandError("No se generó el evento demo esperado.")
        generation = SearchGeneration.objects.filter(
            organization=organization, status=GenerationStatus.ACTIVE
        ).first()
        if generation is None:
            generation = rebuild_search_index(organization=organization)
        notification, created = Notification.objects.get_or_create(
            event=event,
            recipient=recipient,
            template_key="demo.platform_operations",
            defaults={
                "organization": organization,
                "category": NotificationCategory.SYSTEM,
                "title": "Centro de operaciones listo",
                "body": "La búsqueda y las notificaciones demo están disponibles.",
                "action_url": f"/organizaciones/{organization.slug}/buscar",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo operacional listo: generación {generation.number}; "
                f"notificación {'creada' if created else 'conservada'} {notification.id}. "
                "No se creó EmailDelivery."
            )
        )
