# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
import uuid
from io import StringIO
from unittest.mock import MagicMock, patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from domain.events.models import DomainEvent
from domain.organizations.choices import RoleCode
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)

from .models import (
    EmailDelivery,
    EmailDeliveryStatus,
    Notification,
    NotificationCategory,
    NotificationDeliveryEvent,
    NotificationPreference,
)
from .preferences import effective_preference
from .routing import NotificationRoute, route_event
from .services import (
    archive_notification,
    mark_all_read,
    mark_read,
    replace_preferences,
    route_domain_event,
)
from .tasks import send_email_delivery


class NotificationTests(TestCase):
    @patch(
        "domain.notifications.management.commands.check_smtp_connection.get_connection"
    )
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="smtp.example.test",
        EMAIL_PORT=587,
    )
    def test_smtp_check_authenticates_without_sending(
        self, connection_factory: MagicMock
    ) -> None:
        connection = connection_factory.return_value
        output = StringIO()

        call_command("check_smtp_connection", stdout=output)

        connection.open.assert_called_once_with()
        connection.close.assert_called_once_with()
        self.assertIn("no se envió ningún correo", output.getvalue())

    @patch(
        "domain.notifications.management.commands.send_smtp_test_email."
        "EmailMultiAlternatives.send",
        return_value=1,
    )
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="Plataforma Académica <cuentas@example.test>",
    )
    def test_smtp_send_requires_confirmation_and_builds_message(
        self, send: MagicMock
    ) -> None:
        with self.assertRaisesMessage(CommandError, "Se requiere --confirm"):
            call_command("send_smtp_test_email", to="recipient@example.test")

        output = StringIO()
        call_command(
            "send_smtp_test_email",
            to="recipient@example.test",
            confirm=True,
            stdout=output,
        )

        send.assert_called_once_with(fail_silently=False)
        self.assertIn("Correo de prueba transmitido", output.getvalue())

    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="notification-owner@example.test",
            password="StrongNotificationPassword!42",
        )
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=True,
        )
        self.other = get_user_model().objects.create_user(
            email="notification-other@example.test",
            password="StrongNotificationPassword!42",
        )
        governance_owner = get_user_model().objects.create_user(
            email="notification-governance-owner@example.test",
            password="StrongNotificationPassword!42",
        )
        self.organization = create_organization_with_owner(
            actor=governance_owner, name="Avisos", slug="avisos"
        )
        add_existing_member_with_roles(
            actor=governance_owner,
            organization=self.organization,
            user=self.user,
            roles={RoleCode.ADMINISTRATOR},
        )
        self.event = DomainEvent.objects.create(
            event_type="learning.enrollment.suspended.v1",
            schema_version=1,
            organization=self.organization,
            aggregate_type="enrollment",
            aggregate_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            payload={"enrollment_id": str(uuid.uuid4())},
            occurred_at=timezone.now(),
        )
        self.notification = Notification.objects.create(
            organization=self.organization,
            recipient=self.user,
            event=self.event,
            category=NotificationCategory.LEARNING,
            template_key="enrollment_suspended",
            title="Acceso suspendido",
            body="Tu acceso fue suspendido.",
            action_url=f"/organizaciones/{self.organization.slug}/aprendizaje",
        )

    def test_read_archive_preferences_and_default_without_extra_row(self) -> None:
        self.assertTrue(
            effective_preference(self.user, NotificationCategory.LEARNING).email_enabled
        )
        self.assertEqual(NotificationPreference.objects.count(), 0)
        mark_read(notification=self.notification, read=True)
        self.assertIsNotNone(self.notification.read_at)
        self.assertEqual(mark_all_read(user=self.user), 0)
        archive_notification(notification=self.notification)
        self.assertIsNotNone(self.notification.archived_at)
        replace_preferences(
            user=self.user,
            values={
                NotificationCategory.ASSESSMENT: {
                    "in_app_enabled": True,
                    "email_enabled": False,
                }
            },
        )
        self.assertFalse(
            effective_preference(
                self.user, NotificationCategory.ASSESSMENT
            ).email_enabled
        )

    def test_immutable_fields_dedup_and_idor(self) -> None:
        self.notification.title = "Mutación"
        with self.assertRaises(ValidationError):
            self.notification.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Notification.objects.create(
                organization=self.organization,
                recipient=self.user,
                event=self.event,
                category=NotificationCategory.LEARNING,
                template_key="enrollment_suspended",
                title="Duplicada",
                body="Duplicada",
            )
        client = APIClient()
        client.force_authenticate(user=self.other)
        response = client.post(f"/api/v1/notifications/{self.notification.id}/read/")
        self.assertEqual(response.status_code, 404)

    def test_notification_api_complete_owner_flow(self) -> None:
        client = APIClient()
        client.force_authenticate(user=self.user)
        self.assertEqual(client.get("/api/v1/notifications/?page=bad").status_code, 400)
        listing = client.get("/api/v1/notifications/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["pagination"]["total"], 1)
        self.assertEqual(
            client.get("/api/v1/notifications/unread-count/").data["count"], 1
        )
        self.assertEqual(
            client.post(
                f"/api/v1/notifications/{self.notification.id}/read/"
            ).status_code,
            200,
        )
        self.assertEqual(
            client.post(
                f"/api/v1/notifications/{self.notification.id}/unread/"
            ).status_code,
            200,
        )
        self.assertEqual(
            client.post("/api/v1/notifications/read-all/").status_code, 200
        )
        preferences = client.get("/api/v1/notifications/preferences/")
        self.assertEqual(preferences.status_code, 200)
        self.assertEqual(len(preferences.data["preferences"]), 6)
        updated = client.put(
            "/api/v1/notifications/preferences/",
            {
                "preferences": [
                    {
                        "category": NotificationCategory.ASSET,
                        "in_app_enabled": True,
                        "email_enabled": False,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            client.post(
                f"/api/v1/notifications/{self.notification.id}/archive/"
            ).status_code,
            200,
        )
        self.assertEqual(
            client.get("/api/v1/notifications/").data["pagination"]["total"], 0
        )

    @patch("domain.notifications.tasks.send_email_delivery.delay")
    @patch("domain.notifications.services.route_event")
    def test_event_routing_is_idempotent_and_email_delivery_succeeds(
        self, route_mock: object, delay_mock: object
    ) -> None:
        EmailAddress.objects.create(
            user=self.other, email=self.other.email, primary=True, verified=True
        )
        route_mock.return_value = NotificationRoute(  # type: ignore[attr-defined]
            (self.other.id,),
            NotificationCategory.SYSTEM,
            "controlled_notice",
            "Aviso controlado",
            "Mensaje operacional sin datos sensibles.",
            f"/organizaciones/{self.organization.slug}/notificaciones",
        )
        with self.captureOnCommitCallbacks(execute=True):
            route_domain_event(self.event)
            route_domain_event(self.event)
        delivery = EmailDelivery.objects.get(recipient=self.other)
        self.assertEqual(Notification.objects.filter(recipient=self.other).count(), 1)
        delay_mock.assert_called_once_with(str(delivery.id))  # type: ignore[attr-defined]
        send_email_delivery(str(delivery.id))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, EmailDeliveryStatus.SENT)
        self.assertTrue(delivery.message_id)
        self.assertEqual(len(mail.outbox), 1)
        send_email_delivery(str(delivery.id))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            list(delivery.events.values_list("status", flat=True)),
            [EmailDeliveryStatus.SENDING, EmailDeliveryStatus.SENT],
        )

    def test_email_terminal_failure_and_operations_retry_api(self) -> None:
        delivery = EmailDelivery.objects.create(
            notification=self.notification,
            recipient=self.other,
            template_key=self.notification.template_key,
            recipient_email_hash="0" * 64,
        )
        send_email_delivery(str(delivery.id))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, EmailDeliveryStatus.DEAD)
        self.assertEqual(delivery.last_error_code, "recipient_unavailable")
        self.assertEqual(
            NotificationDeliveryEvent.objects.filter(delivery=delivery).count(), 2
        )
        client = APIClient()
        client.force_authenticate(user=self.user)
        self.assertEqual(
            client.get("/api/v1/platform/email-deliveries/").status_code, 200
        )
        with patch("domain.notifications.api.views.send_email_delivery.delay") as retry:
            response = client.post(
                f"/api/v1/platform/email-deliveries/{delivery.id}/retry/"
            )
        self.assertEqual(response.status_code, 202)
        retry.assert_called_once_with(str(delivery.id))
        self.assertEqual(
            client.post(
                f"/api/v1/platform/email-deliveries/{delivery.id}/retry/"
            ).status_code,
            409,
        )

    def test_platform_operator_without_membership_cannot_read_or_retry_foreign_email(
        self,
    ) -> None:
        foreign_owner = get_user_model().objects.create_user(
            email="foreign-notification-owner@example.test",
            password="StrongNotificationPassword!42",
        )
        foreign_organization = create_organization_with_owner(
            actor=foreign_owner, name="Avisos ajenos", slug="avisos-ajenos"
        )
        foreign_event = DomainEvent.objects.create(
            event_type="learning.enrollment.suspended.v1",
            schema_version=1,
            organization=foreign_organization,
            aggregate_type="enrollment",
            aggregate_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            payload={"enrollment_id": str(uuid.uuid4())},
            occurred_at=timezone.now(),
        )
        foreign_notification = Notification.objects.create(
            organization=foreign_organization,
            recipient=foreign_owner,
            event=foreign_event,
            category=NotificationCategory.LEARNING,
            template_key="enrollment_suspended",
            title="Acceso suspendido",
            body="Tu acceso fue suspendido.",
        )
        foreign_delivery = EmailDelivery.objects.create(
            notification=foreign_notification,
            recipient=foreign_owner,
            template_key=foreign_notification.template_key,
            recipient_email_hash="1" * 64,
        )
        operator = get_user_model().objects.create_superuser(
            email="notifications-operator@example.test",
            password="StrongNotificationPassword!42",
        )
        client = APIClient()
        client.force_authenticate(user=operator)

        listing = client.get("/api/v1/platform/email-deliveries/")
        retry = client.post(
            f"/api/v1/platform/email-deliveries/{foreign_delivery.id}/retry/"
        )

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data, [])
        self.assertEqual(retry.status_code, 404)

    @patch("domain.notifications.routing._regrade_route")
    @patch("domain.notifications.routing._publication_route")
    @patch("domain.notifications.routing._assessment_revision_route")
    @patch("domain.notifications.routing._course_revision_route")
    @patch("domain.notifications.routing._asset_route")
    @patch("domain.notifications.routing._attempt_route")
    @patch("domain.notifications.routing._enrollment_route")
    def test_route_dispatch_table_covers_supported_event_families(
        self,
        enrollment: object,
        attempt: object,
        asset: object,
        course_revision: object,
        assessment_revision: object,
        publication: object,
        regrade: object,
    ) -> None:
        sentinel = NotificationRoute((), NotificationCategory.SYSTEM, "x", "x", "x", "")
        for mock in (
            enrollment,
            attempt,
            asset,
            course_revision,
            assessment_revision,
            publication,
            regrade,
        ):
            mock.return_value = sentinel  # type: ignore[attr-defined]
        cases = (
            "learning.enrollment.created.v1",
            "assessments.attempt.graded.v1",
            "assessments.attempt.pending_manual.v1",
            "assets.asset_version.ready.v1",
            "courses.revision.changes_requested.v1",
            "assessments.question_revision.changes_requested.v1",
            "assessments.assessment_revision.changes_requested.v1",
            "publishing.course_release.published.v1",
            "publishing.course_publication.withdrawn.v1",
            "assessments.regrade.completed.v1",
        )
        for event_type in cases:
            self.event.event_type = event_type
            self.assertEqual(route_event(self.event), sentinel)
        self.event.event_type = "learning.course_progress.completed.v1"
        self.assertIsNone(route_event(self.event))
