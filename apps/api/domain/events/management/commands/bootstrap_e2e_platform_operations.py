# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from domain.courses.models import Course
from domain.discovery.services import rebuild_search_index
from domain.events.models import DeliveryStatus, EventConsumerDelivery
from domain.events.services import process_delivery
from domain.identity.models import User
from domain.notifications.models import EmailDelivery, EmailDeliveryStatus
from domain.notifications.tasks import send_email_delivery
from domain.organizations.models import Organization
from domain.publishing.models import CoursePublication
from domain.publishing.services import publish_approved_revision


class Command(BaseCommand):
    help = "Crea fixtures efímeros de búsqueda/eventos/notificaciones para Playwright."

    def handle(self, *args: object, **options: object) -> None:
        if settings.SETTINGS_MODULE != "config.settings.e2e":
            raise CommandError("Este comando sólo puede ejecutarse con settings E2E.")
        organization = Organization.objects.get(slug="organizacion-a")
        owner = User.objects.get(email="owner@organizations.e2e.test")
        course = Course.objects.get(
            organization=organization, slug="publicacion-inmutable-e2e"
        )
        publication = CoursePublication.objects.filter(course=course).first()
        if publication is None:
            revision = course.revisions.get(authoring_status="approved")
            publish_approved_revision(
                actor=owner,
                organization=organization,
                course=course,
                revision=revision,
                expected_publication_version=0,
            )
        call_command("bootstrap_e2e_learning")
        call_command("bootstrap_e2e_assessments")
        rebuild_search_index(organization=organization, actor=owner)
        for delivery in EventConsumerDelivery.objects.filter(
            status=DeliveryStatus.PENDING
        ).order_by("created_at", "id"):
            process_delivery(delivery.id)
        for delivery_id in EmailDelivery.objects.filter(
            status=EmailDeliveryStatus.QUEUED
        ).values_list("id", flat=True):
            send_email_delivery(str(delivery_id))
        replay_delivery = EventConsumerDelivery.objects.filter(
            event__event_type="learning.enrollment.created.v1",
            consumer_name="notifications.domain_event_router.v1",
        ).first()
        if replay_delivery is None:
            raise CommandError("Falta el delivery E2E requerido para replay.")
        replay_delivery.status = DeliveryStatus.DEAD
        replay_delivery.attempt_count = 5
        replay_delivery.claimed_at = None
        replay_delivery.lease_expires_at = None
        replay_delivery.next_attempt_at = None
        replay_delivery.last_error_code = "e2e_forced_terminal"
        replay_delivery.processed_at = None
        replay_delivery.save()
        self.stdout.write(
            self.style.SUCCESS(
                "Fixtures E2E operacionales creados con índice, avisos y correo aislado."
            )
        )
