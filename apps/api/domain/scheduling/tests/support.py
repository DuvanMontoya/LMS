from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone

from domain.learning.tests.support import LearningFixtureMixin
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.scheduling.choices import EventType
from domain.scheduling.livekit_gateway import LiveKitConfiguration
from domain.scheduling.services import create_event_series


class FakeLiveKitGateway:
    def __init__(self) -> None:
        self.config = LiveKitConfiguration(
            server_url="wss://livekit.example.test",
            api_key="devkey",
            api_secret="secret-secret-secret-secret-secret",
            token_ttl_seconds=300,
            room_empty_timeout_seconds=600,
            max_participants=250,
        )
        self.created_rooms: list[str] = []
        self.closed_rooms: list[str] = []
        self.permission_changes: list[dict[str, object]] = []
        self.removed: list[str] = []

    def create_room(self, *, room_name: str, metadata: str):
        del metadata
        self.created_rooms.append(room_name)
        return SimpleNamespace(sid="RM_test")

    def close_room(self, *, room_name: str) -> None:
        self.closed_rooms.append(room_name)

    def issue_token(self, *, user_id: object, room_name: str, access) -> str:
        return f"token:{user_id}:{room_name}:{access.role}"

    def update_participant_permissions(self, **values: object) -> None:
        self.permission_changes.append(values)

    def remove_participant(self, *, room_name: str, identity: str) -> None:
        del room_name
        self.removed.append(identity)


class SchedulingFixtureMixin(LearningFixtureMixin):
    def scheduling_context(self):
        (
            owner,
            learner,
            organization,
            learner_membership,
            revision,
            _module,
            _unit,
            _publication,
            _release,
            enrollment,
        ) = self.learning_context()
        host = self.member(
            owner,
            organization,
            RoleCode.INSTRUCTOR,
            "scheduling-host@example.test",
        )
        host_membership = Membership.objects.get(organization=organization, user=host)
        starts_at = timezone.now() + timedelta(minutes=2)
        series = create_event_series(
            actor=owner,
            organization=organization,
            course=revision.course,
            host_membership=host_membership,
            title="Álgebra en vivo",
            description="Sesión sincrónica",
            event_type=EventType.LIVE_CLASS,
            timezone_name="America/Bogota",
            first_starts_at=starts_at,
            duration_minutes=60,
        )
        occurrence = series.occurrences.select_related("live_session").get()
        return {
            "owner": owner,
            "host": host,
            "learner": learner,
            "organization": organization,
            "learner_membership": learner_membership,
            "course": revision.course,
            "enrollment": enrollment,
            "series": series,
            "occurrence": occurrence,
            "session": occurrence.live_session,
        }
