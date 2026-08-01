from __future__ import annotations

import base64
import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from domain.scheduling.choices import AttendanceRole, LiveSessionStatus, RecurrenceScope
from domain.scheduling.exceptions import (
    LiveSessionClosed,
    LiveSessionOutsideWindow,
    SchedulingAccessDenied,
    SchedulingConflict,
)
from domain.scheduling.livekit_gateway import LiveKitGateway
from domain.scheduling.policies import LiveAccess
from domain.scheduling.services import (
    cancel_occurrence,
    end_live_session,
    join_live_session,
    reschedule_occurrence,
    start_live_session,
)

from .support import FakeLiveKitGateway, SchedulingFixtureMixin


class SchedulingServiceTests(SchedulingFixtureMixin, TestCase):
    def test_short_lived_token_has_pseudonymous_identity_and_least_privilege(
        self,
    ) -> None:
        gateway = LiveKitGateway(FakeLiveKitGateway().config)
        token = gateway.issue_token(
            user_id="00000000-0000-0000-0000-000000000123",
            room_name="lk_test",
            access=LiveAccess(
                role=AttendanceRole.STUDENT,
                can_publish=True,
                can_share_screen=False,
                can_moderate=False,
            ),
        )
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        self.assertEqual(claims["sub"], "user:00000000-0000-0000-0000-000000000123")
        self.assertEqual(claims["attributes"]["lms.role"], "student")
        self.assertLessEqual(claims["exp"] - claims["nbf"], 300)
        self.assertFalse(claims["video"]["canPublishData"])
        self.assertNotIn("screen_share", claims["video"]["canPublishSources"])

    def test_room_name_is_random_and_not_exposed_until_join(self) -> None:
        context = self.scheduling_context()
        session = context["session"]
        self.assertRegex(session.room_name, r"^lk_[0-9a-f]{32}$")
        self.assertNotIn(str(context["course"].id), session.room_name)

    def test_host_start_is_idempotent_and_learner_joins_after_start(self) -> None:
        context = self.scheduling_context()
        gateway = FakeLiveKitGateway()
        first = start_live_session(
            actor=context["owner"], session_id=context["session"].id, gateway=gateway
        )
        second = start_live_session(
            actor=context["owner"], session_id=context["session"].id, gateway=gateway
        )
        learner = join_live_session(
            actor=context["learner"], session_id=context["session"].id, gateway=gateway
        )
        self.assertEqual(len(gateway.created_rooms), 1)
        self.assertEqual(first["session"]["role"], "host")
        self.assertEqual(second["session"]["status"], LiveSessionStatus.LIVE)
        self.assertEqual(learner["session"]["role"], "student")
        self.assertFalse(learner["session"]["canShareScreen"])

    def test_learner_cannot_start_or_end(self) -> None:
        context = self.scheduling_context()
        gateway = FakeLiveKitGateway()
        with self.assertRaises(SchedulingAccessDenied):
            start_live_session(
                actor=context["learner"],
                session_id=context["session"].id,
                gateway=gateway,
            )
        start_live_session(
            actor=context["owner"], session_id=context["session"].id, gateway=gateway
        )
        with self.assertRaises(SchedulingAccessDenied):
            end_live_session(
                actor=context["learner"],
                session_id=context["session"].id,
                gateway=gateway,
            )

    def test_reschedule_requires_expected_version_and_preserves_room(self) -> None:
        context = self.scheduling_context()
        occurrence = context["occurrence"]
        room_name = context["session"].room_name
        with self.assertRaises(SchedulingConflict):
            reschedule_occurrence(
                actor=context["owner"],
                occurrence_id=occurrence.id,
                expected_version=99,
                starts_at=occurrence.starts_at + timedelta(days=1),
                ends_at=occurrence.ends_at + timedelta(days=1),
                scope=RecurrenceScope.OCCURRENCE,
            )
        changed = reschedule_occurrence(
            actor=context["owner"],
            occurrence_id=occurrence.id,
            expected_version=1,
            starts_at=occurrence.starts_at + timedelta(days=1),
            ends_at=occurrence.ends_at + timedelta(days=1),
            scope=RecurrenceScope.OCCURRENCE,
        )
        self.assertEqual(changed.live_session.room_name, room_name)
        self.assertEqual(changed.lock_version, 2)

    def test_cancelled_session_cannot_be_joined(self) -> None:
        context = self.scheduling_context()
        occurrence = cancel_occurrence(
            actor=context["owner"],
            occurrence_id=context["occurrence"].id,
            expected_version=1,
            scope=RecurrenceScope.OCCURRENCE,
        )
        self.assertEqual(occurrence.live_session.status, LiveSessionStatus.CANCELLED)
        with self.assertRaises(LiveSessionClosed):
            join_live_session(
                actor=context["learner"],
                session_id=context["session"].id,
                gateway=FakeLiveKitGateway(),
            )

    def test_outside_join_window_is_rejected(self) -> None:
        context = self.scheduling_context()
        occurrence = context["occurrence"]
        occurrence.starts_at = timezone.now() + timedelta(days=2)
        occurrence.ends_at = occurrence.starts_at + timedelta(hours=1)
        occurrence.save(update_fields=("starts_at", "ends_at", "updated_at"))
        with self.assertRaises(LiveSessionOutsideWindow):
            start_live_session(
                actor=context["owner"],
                session_id=context["session"].id,
                gateway=FakeLiveKitGateway(),
            )
