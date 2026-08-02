from __future__ import annotations

import base64
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from domain.learning.choices import AcademicGroupLevel, AcademicGroupRole
from domain.learning.services import (
    confirm_cohort_roster_sync,
    create_academic_group,
    create_cohort,
    make_enrollment_individual,
    replace_academic_group_roster,
)
from domain.organizations.models import Membership
from domain.scheduling.choices import (
    AttendanceRole,
    EventType,
    LiveSessionStatus,
    RecurrenceScope,
)
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
    create_event_series,
    end_live_session,
    join_live_session,
    reschedule_occurrence,
    start_live_session,
)

from .support import FakeLiveKitGateway, SchedulingFixtureMixin


class SchedulingServiceTests(SchedulingFixtureMixin, TestCase):
    def test_course_group_session_requires_current_group_assignment(self) -> None:
        context = self.scheduling_context()
        group = create_academic_group(
            actor=context["owner"],
            organization=context["organization"],
            name="Grupo de agenda",
            academic_year=2026,
            level=AcademicGroupLevel.SECONDARY_11,
        )
        group = replace_academic_group_roster(
            actor=context["owner"],
            group=group,
            expected_group_version=group.lock_version,
            members=[
                {
                    "membership_id": context["learner_membership"].id,
                    "role": AcademicGroupRole.LEARNER,
                }
            ],
        )
        cohort = create_cohort(
            actor=context["owner"],
            organization=context["organization"],
            course=context["course"],
            release=context["enrollment"].current_release_assignment.release,
            migration_review_required=True,
            academic_group=group,
            name="Álgebra grupo de agenda",
        )
        confirm_cohort_roster_sync(
            actor=context["owner"],
            cohort=cohort,
            expected_cohort_version=cohort.lock_version,
            expected_academic_group_version=group.lock_version,
            reason="Prueba de audiencia",
        )
        series = create_event_series(
            actor=context["owner"],
            organization=context["organization"],
            course=context["course"],
            course_group=cohort,
            host_membership=context["series"].host_membership,
            title="Clase sólo del grupo",
            description="Audiencia por matrícula de grupo",
            event_type=EventType.LIVE_CLASS,
            timezone_name="America/Bogota",
            first_starts_at=timezone.now() + timedelta(minutes=2),
            duration_minutes=45,
        )
        session = series.occurrences.select_related("live_session").get().live_session
        gateway = FakeLiveKitGateway()
        start_live_session(
            actor=context["owner"], session_id=session.id, gateway=gateway
        )
        self.assertEqual(
            join_live_session(
                actor=context["learner"], session_id=session.id, gateway=gateway
            )["session"]["role"],
            "student",
        )

        context["enrollment"].refresh_from_db()
        make_enrollment_individual(
            actor=context["owner"],
            enrollment=context["enrollment"],
            expected_version=context["enrollment"].lock_version,
            reason="Excepción individual de prueba",
        )
        with self.assertRaises(SchedulingAccessDenied):
            join_live_session(
                actor=context["learner"], session_id=session.id, gateway=gateway
            )

    def test_standalone_session_is_visible_only_to_explicit_participants(self) -> None:
        context = self.scheduling_context()
        outsider = get_user_model().objects.create_user(
            email="standalone-outsider@example.test", password="StrongPassword!42"
        )
        Membership.objects.create(
            organization=context["organization"],
            user=outsider,
            status_changed_by=context["owner"],
            status_changed_at=timezone.now(),
        )
        series = create_event_series(
            actor=context["owner"],
            organization=context["organization"],
            course=None,
            host_membership=context["series"].host_membership,
            participant_memberships=[context["learner_membership"]],
            title="Tutoría particular",
            description="Tema independiente",
            event_type=EventType.LIVE_CLASS,
            timezone_name="America/Bogota",
            first_starts_at=timezone.now() + timedelta(minutes=2),
            duration_minutes=45,
        )
        session = series.occurrences.select_related("live_session").get().live_session
        gateway = FakeLiveKitGateway()
        start_live_session(
            actor=context["owner"], session_id=session.id, gateway=gateway
        )
        payload = join_live_session(
            actor=context["learner"], session_id=session.id, gateway=gateway
        )
        self.assertEqual(payload["session"]["role"], "student")
        with self.assertRaises(SchedulingAccessDenied):
            join_live_session(actor=outsider, session_id=session.id, gateway=gateway)

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
