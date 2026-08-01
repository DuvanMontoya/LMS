# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from domain.organizations.services import create_organization_with_owner

from .models import DeliveryStatus, DomainEvent, EventConsumerDelivery
from .services import process_delivery, record_domain_event


class DomainEventTransactionTests(TestCase):
    def setUp(self) -> None:
        self.owner = get_user_model().objects.create_user(
            email="events-owner@example.test", password="StrongEventsPassword!42"
        )
        self.organization = create_organization_with_owner(
            actor=self.owner, name="Eventos", slug="eventos"
        )

    @patch("domain.events.tasks.dispatch_domain_event.delay")
    def test_commit_records_event_deliveries_and_dispatches_after_commit(
        self, dispatch: object
    ) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                event = record_domain_event(
                    event_type="learning.enrollment.created.v1",
                    organization=self.organization,
                    aggregate_type="enrollment",
                    aggregate_id=uuid.uuid4(),
                    actor=self.owner,
                    payload={"enrollment_id": str(uuid.uuid4())},
                )
                self.assertTrue(DomainEvent.objects.filter(pk=event.pk).exists())
        self.assertGreaterEqual(
            EventConsumerDelivery.objects.filter(event=event).count(), 1
        )
        dispatch.assert_called_once_with(str(event.id))  # type: ignore[attr-defined]

    def test_rollback_leaves_no_event(self) -> None:
        marker = uuid.uuid4()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                record_domain_event(
                    event_type="learning.enrollment.created.v1",
                    organization=self.organization,
                    aggregate_type="enrollment",
                    aggregate_id=marker,
                    payload={"enrollment_id": str(marker)},
                )
                raise RuntimeError("rollback")
        self.assertFalse(DomainEvent.objects.filter(aggregate_id=marker).exists())

    def test_event_schema_rejects_extra_or_sensitive_fields(self) -> None:
        with self.assertRaises(ValueError), transaction.atomic():
            record_domain_event(
                event_type="learning.enrollment.created.v1",
                organization=self.organization,
                aggregate_type="enrollment",
                aggregate_id=uuid.uuid4(),
                payload={
                    "enrollment_id": str(uuid.uuid4()),
                    "password": "must-not-persist",
                },
            )

    def test_platform_operator_without_membership_cannot_read_foreign_events(
        self,
    ) -> None:
        event = DomainEvent.objects.create(
            event_type="learning.enrollment.created.v1",
            schema_version=1,
            organization=self.organization,
            aggregate_type="enrollment",
            aggregate_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            payload={"enrollment_id": str(uuid.uuid4())},
            occurred_at=timezone.now(),
        )
        operator = get_user_model().objects.create_superuser(
            email="events-operator@example.test", password="StrongEventsPassword!42"
        )
        client = APIClient()
        client.force_authenticate(user=operator)

        listing = client.get("/api/v1/platform/events/")
        detail = client.get(f"/api/v1/platform/events/{event.id}/")

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data, [])
        self.assertEqual(detail.status_code, 404)

    def _delivery(self) -> EventConsumerDelivery:
        with transaction.atomic():
            event = record_domain_event(
                event_type="learning.enrollment.created.v1",
                organization=self.organization,
                aggregate_type="enrollment",
                aggregate_id=uuid.uuid4(),
                payload={"enrollment_id": str(uuid.uuid4())},
            )
        delivery = EventConsumerDelivery.objects.filter(event=event).first()
        assert delivery is not None
        return delivery

    def test_event_requires_atomic_transaction(self) -> None:
        with (
            patch("domain.events.services.connection.in_atomic_block", False),
            self.assertRaises(RuntimeError),
        ):
            record_domain_event(
                event_type="learning.enrollment.created.v1",
                organization=self.organization,
                aggregate_type="enrollment",
                aggregate_id=uuid.uuid4(),
                payload={"enrollment_id": str(uuid.uuid4())},
            )

    @patch("domain.events.registry.consumer_definition")
    def test_delivery_success_is_idempotent_and_active_lease_is_respected(
        self, definition: object
    ) -> None:
        handler_calls: list[uuid.UUID] = []

        def handler(event: DomainEvent) -> None:
            handler_calls.append(event.id)

        definition.return_value = SimpleNamespace(  # type: ignore[attr-defined]
            handler=handler
        )
        delivery = self._delivery()
        self.assertEqual(process_delivery(delivery.id), DeliveryStatus.COMPLETED)
        self.assertEqual(process_delivery(delivery.id), DeliveryStatus.COMPLETED)
        self.assertEqual(len(handler_calls), 1)

        leased = self._delivery()
        leased.status = DeliveryStatus.PROCESSING
        leased.lease_expires_at = timezone.now() + timedelta(minutes=1)
        leased.save(update_fields=("status", "lease_expires_at"))
        self.assertEqual(process_delivery(leased.id), DeliveryStatus.PROCESSING)

    @patch("domain.events.registry.consumer_definition")
    def test_delivery_retries_then_becomes_dead(self, definition: object) -> None:
        def failing_handler(_event: DomainEvent) -> None:
            raise RuntimeError("boom")

        definition.return_value = SimpleNamespace(  # type: ignore[attr-defined]
            handler=failing_handler
        )
        delivery = self._delivery()
        with patch("domain.events.tasks.dispatch_domain_event.apply_async") as retry:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(process_delivery(delivery.id), DeliveryStatus.FAILED)
        retry.assert_called_once()
        delivery.refresh_from_db()
        self.assertIsNotNone(delivery.next_attempt_at)
        delivery.status = DeliveryStatus.PENDING
        delivery.attempt_count = 4
        delivery.save(update_fields=("status", "attempt_count"))
        self.assertEqual(process_delivery(delivery.id), DeliveryStatus.DEAD)
        delivery.refresh_from_db()
        self.assertEqual(delivery.last_error_code, "consumer_failed")
        self.assertIsNone(delivery.next_attempt_at)


class DomainEventTriggerTests(TransactionTestCase):
    reset_sequences = False

    def test_database_trigger_blocks_update_and_delete(self) -> None:
        owner = get_user_model().objects.create_user(
            email="trigger-owner@example.test", password="StrongEventsPassword!42"
        )
        organization = create_organization_with_owner(
            actor=owner, name="Trigger", slug="trigger"
        )
        with transaction.atomic():
            event = record_domain_event(
                event_type="learning.enrollment.created.v1",
                organization=organization,
                aggregate_type="enrollment",
                aggregate_id=uuid.uuid4(),
                payload={"enrollment_id": str(uuid.uuid4())},
            )
        with self.assertRaises(DatabaseError), transaction.atomic():
            DomainEvent.objects.filter(pk=event.pk).update(aggregate_type="changed")
        with self.assertRaises(DatabaseError), transaction.atomic():
            DomainEvent.objects.filter(pk=event.pk).delete()
