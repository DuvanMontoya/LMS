from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from livekit import api
from rest_framework.test import APIClient

from domain.scheduling.choices import LiveSessionStatus
from domain.scheduling.livekit_gateway import LiveKitConfiguration, LiveKitGateway
from domain.scheduling.models import AttendanceSegment, LiveKitWebhookEvent
from domain.scheduling.webhooks import receive_and_process_webhook

from .support import SchedulingFixtureMixin

LIVEKIT_SETTINGS = {
    "LIVEKIT_ENABLED": True,
    "LIVEKIT_URL": "wss://livekit.example.test",
    "LIVEKIT_API_KEY": "devkey",
    "LIVEKIT_API_SECRET": "secret-secret-secret-secret-secret",
}


def signed_webhook(payload: dict[str, object]) -> tuple[bytes, str]:
    raw = json.dumps(payload, separators=(",", ":"))
    digest = base64.b64encode(hashlib.sha256(raw.encode()).digest()).decode()
    token = (
        api.AccessToken(
            LIVEKIT_SETTINGS["LIVEKIT_API_KEY"],
            LIVEKIT_SETTINGS["LIVEKIT_API_SECRET"],
        )
        .with_sha256(digest)
        .to_jwt()
    )
    return raw.encode(), token


@override_settings(**LIVEKIT_SETTINGS)
class SchedulingApiAndWebhookTests(SchedulingFixtureMixin, TestCase):
    def test_calendar_feed_is_scoped_and_never_leaks_room_or_token(self) -> None:
        context = self.scheduling_context()
        client = APIClient()
        client.force_authenticate(context["learner"])
        occurrence = context["occurrence"]
        response = client.get(
            f"/api/v1/organizations/{context['organization'].slug}/scheduling/calendar/events/",
            {
                "start": (occurrence.starts_at - timedelta(days=1)).isoformat(),
                "end": (occurrence.ends_at + timedelta(days=1)).isoformat(),
                "timeZone": "America/Bogota",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        serialized = json.dumps(body)
        self.assertNotIn("room_name", serialized)
        self.assertNotIn("roomName", serialized)
        self.assertNotIn("token", serialized)

    def test_cross_organization_session_is_not_found(self) -> None:
        context = self.scheduling_context()
        other_owner, other_org, *_ = self.curriculum("-other")
        client = APIClient()
        client.force_authenticate(other_owner)
        response = client.get(
            f"/api/v1/organizations/{other_org.slug}/scheduling/live-sessions/{context['session'].id}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_signed_webhooks_are_idempotent_and_track_segments(self) -> None:
        context = self.scheduling_context()
        session = context["session"]
        session.status = LiveSessionStatus.LIVE
        session.actual_started_at = timezone.now()
        session.save(update_fields=("status", "actual_started_at", "updated_at"))
        event_id = str(uuid.uuid4())
        created_at = int(timezone.now().timestamp())
        joined = {
            "id": event_id,
            "event": "participant_joined",
            "createdAt": str(created_at),
            "room": {"name": session.room_name, "sid": "RM_test"},
            "participant": {
                "identity": f"user:{context['learner'].id}",
                "sid": "PA_test",
                "attributes": {"lms.role": "student"},
            },
        }
        body, token = signed_webhook(joined)
        gateway = LiveKitGateway(
            LiveKitConfiguration(
                server_url=LIVEKIT_SETTINGS["LIVEKIT_URL"],
                api_key=LIVEKIT_SETTINGS["LIVEKIT_API_KEY"],
                api_secret=LIVEKIT_SETTINGS["LIVEKIT_API_SECRET"],
                token_ttl_seconds=300,
                room_empty_timeout_seconds=600,
                max_participants=250,
            )
        )
        first, created = receive_and_process_webhook(
            body=body, authorization=token, gateway=gateway
        )
        duplicate, created_again = receive_and_process_webhook(
            body=body, authorization=token, gateway=gateway
        )
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, duplicate.pk)
        self.assertEqual(LiveKitWebhookEvent.objects.count(), 1)
        self.assertEqual(AttendanceSegment.objects.count(), 1)

        left = {
            **joined,
            "id": str(uuid.uuid4()),
            "event": "participant_left",
            "createdAt": str(created_at + 75),
        }
        left_body, left_token = signed_webhook(left)
        receive_and_process_webhook(
            body=left_body, authorization=left_token, gateway=gateway
        )
        segment = AttendanceSegment.objects.get()
        self.assertEqual(segment.duration_seconds, 75)
        self.assertIsNotNone(segment.left_event_id)

    def test_invalid_webhook_signature_is_rejected_by_endpoint(self) -> None:
        client = APIClient()
        response = client.post(
            "/api/v1/livekit/webhook/",
            data=b"{}",
            content_type="application/webhook+json",
            HTTP_AUTHORIZATION="not-a-token",
        )
        self.assertEqual(response.status_code, 401)
