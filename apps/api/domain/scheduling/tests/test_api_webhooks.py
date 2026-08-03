from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from livekit import api
from rest_framework.test import APIClient

from domain.catalog.services import create_learning_objective
from domain.courses.choices import ActivityCompletionMethod, ActivityType
from domain.courses.models import CourseActivity
from domain.courses.services import create_activity, create_module
from domain.learning.contracts import register_live_session_requirement
from domain.learning.models import (
    ActivityProgress,
    CourseGroupActivity,
    ExternalRequirementCompletion,
)
from domain.learning.services import (
    create_academic_period,
    create_cohort,
    enroll_member,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.scheduling.choices import EventType, LiveSessionStatus
from domain.scheduling.livekit_gateway import LiveKitConfiguration, LiveKitGateway
from domain.scheduling.models import (
    AttendanceSegment,
    LiveClassActivityBinding,
    LiveKitWebhookEvent,
)
from domain.scheduling.services import create_event_series
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
    def test_live_activity_is_created_with_its_attendance_policy_atomically(
        self,
    ) -> None:
        owner, organization, _subject, objective, _topic, revision = (
            self.course_revision()
        )
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Clases en vivo",
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        url = f"/api/v1/organizations/{organization.slug}/scheduling/course-activities/"
        payload = {
            "estimated_duration_minutes": 60,
            "expected_revision_version": revision.lock_version,
            "minimum_attendance_basis_points": 7500,
            "learning_objective_ids": [str(objective.id)],
            "module_id": str(module.id),
            "session_mode": "interactive",
            "chat_enabled": True,
            "student_audio_enabled": True,
            "student_video_enabled": True,
            "student_screen_share_enabled": False,
            "recording_mode": "manual",
            "recording_layout": "speaker",
            "max_participants": 100,
            "room_empty_timeout_seconds": 600,
            "room_departure_timeout_seconds": 30,
            "join_before_minutes": 15,
            "join_after_minutes": 15,
            "required": True,
            "summary": "Resolución guiada.",
            "title": "Tutoría integral",
        }
        created = client.post(url, payload, format="json")
        self.assertEqual(created.status_code, 201)
        activity = CourseActivity.objects.get(pk=created.data["activity_id"])
        self.assertEqual(activity.estimated_duration_minutes, 60)
        self.assertEqual(created.data["minimum_attendance_minutes"], 45)
        self.assertEqual(
            created.data["revision_lock_version"], revision.lock_version + 3
        )
        before = CourseActivity.objects.count()
        conflict = client.post(url, payload, format="json")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(CourseActivity.objects.count(), before)

    def test_live_activity_rejects_an_objective_not_aligned_to_the_course(self) -> None:
        owner, organization, subject, _objective, _topic, revision = (
            self.course_revision()
        )
        foreign_objective = create_learning_objective(
            actor=owner,
            organization=organization,
            subject=subject,
            code="ALG-02",
            statement="Resolver sistemas no alineados con este curso.",
            description="",
            cognitive_level="apply",
        )
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Clases en vivo",
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        before = CourseActivity.objects.count()

        response = client.post(
            f"/api/v1/organizations/{organization.slug}/scheduling/course-activities/",
            {
                "estimated_duration_minutes": 60,
                "expected_revision_version": revision.lock_version,
                "minimum_attendance_basis_points": 7500,
                "learning_objective_ids": [str(foreign_objective.id)],
                "module_id": str(module.id),
                "session_mode": "interactive",
                "chat_enabled": True,
                "student_audio_enabled": True,
                "student_video_enabled": True,
                "student_screen_share_enabled": False,
                "recording_mode": "off",
                "recording_layout": "speaker",
                "max_participants": 100,
                "room_empty_timeout_seconds": 600,
                "room_departure_timeout_seconds": 30,
                "join_before_minutes": 15,
                "join_after_minutes": 15,
                "required": True,
                "summary": "No debe persistirse.",
                "title": "Objetivo ajeno",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "scheduling_invalid")
        self.assertEqual(CourseActivity.objects.count(), before)

    def test_live_activity_configuration_can_be_reopened_and_updated(self) -> None:
        owner, organization, _subject, objective, _topic, revision = (
            self.course_revision()
        )
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Clases en vivo",
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        collection_url = (
            f"/api/v1/organizations/{organization.slug}/scheduling/course-activities/"
        )
        created = client.post(
            collection_url,
            {
                "estimated_duration_minutes": 60,
                "expected_revision_version": revision.lock_version,
                "minimum_attendance_basis_points": 7500,
                "learning_objective_ids": [str(objective.id)],
                "module_id": str(module.id),
                "session_mode": "interactive",
                "chat_enabled": True,
                "student_audio_enabled": True,
                "student_video_enabled": True,
                "student_screen_share_enabled": False,
                "recording_mode": "manual",
                "recording_layout": "speaker",
                "max_participants": 100,
                "room_empty_timeout_seconds": 600,
                "room_departure_timeout_seconds": 30,
                "join_before_minutes": 15,
                "join_after_minutes": 15,
                "required": True,
                "summary": "Configuración inicial.",
                "title": "Tutoría integral",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        activity_id = created.data["activity_id"]
        detail_url = f"{collection_url}{activity_id}/binding/"

        detail = client.get(detail_url)
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.data["chat_enabled"])

        binding_list = client.get(
            f"{collection_url}bindings/", {"revision_id": str(revision.id)}
        )
        self.assertEqual(binding_list.status_code, 200)
        self.assertEqual(len(binding_list.data), 1)
        self.assertEqual(binding_list.data[0]["activity_id"], activity_id)

        updated = client.put(
            detail_url,
            {
                "estimated_duration_minutes": 90,
                "expected_revision_version": created.data["revision_lock_version"],
                "minimum_attendance_basis_points": 6000,
                "learning_objective_ids": [str(objective.id)],
                "session_mode": "webinar",
                "chat_enabled": False,
                "student_audio_enabled": False,
                "student_video_enabled": False,
                "student_screen_share_enabled": False,
                "recording_mode": "automatic",
                "recording_layout": "grid",
                "max_participants": 80,
                "room_empty_timeout_seconds": 300,
                "room_departure_timeout_seconds": 45,
                "join_before_minutes": 20,
                "join_after_minutes": 5,
                "required": False,
                "summary": "Configuración actualizada.",
                "title": "Seminario de aplicaciones",
            },
            format="json",
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.data["revision_lock_version"],
            created.data["revision_lock_version"] + 3,
        )
        activity = CourseActivity.objects.get(pk=activity_id)
        binding = LiveClassActivityBinding.objects.get(activity=activity)
        self.assertEqual(activity.title, "Seminario de aplicaciones")
        self.assertEqual(activity.estimated_duration_minutes, 90)
        self.assertFalse(activity.required)
        self.assertEqual(binding.session_mode, "webinar")
        self.assertFalse(binding.chat_enabled)
        self.assertEqual(binding.recording_mode, "automatic")
        self.assertEqual(binding.minimum_attendance_minutes, 54)
        self.assertEqual(binding.updated_by, owner)

    def test_live_activity_authoring_binds_immutable_attendance_policy(self) -> None:
        owner, organization, _subject, _objective, _topic, revision = (
            self.course_revision()
        )
        module, revision = create_module(
            actor=owner,
            organization=organization,
            revision=revision,
            expected_version=revision.lock_version,
            title="Clases en vivo",
        )
        activity, revision = create_activity(
            actor=owner,
            organization=organization,
            module=module,
            expected_version=revision.lock_version,
            activity_type=ActivityType.LIVE_CLASS,
            title="Tutoría",
            completion_method=ActivityCompletionMethod.ATTENDANCE,
            minimum_attendance_basis_points=7500,
        )
        client = APIClient()
        client.force_authenticate(user=owner)
        url = (
            f"/api/v1/organizations/{organization.slug}/scheduling/"
            f"course-activities/{activity.id}/binding/"
        )
        payload = {
            "expected_revision_version": revision.lock_version,
            "minimum_attended_occurrences": 2,
            "minimum_attendance_minutes": 45,
        }
        created = client.post(url, payload, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["minimum_attended_occurrences"], 2)
        self.assertEqual(created.data["minimum_attendance_minutes"], 45)
        self.assertEqual(
            created.data["revision_lock_version"], revision.lock_version + 1
        )
        duplicate = client.post(
            url,
            {**payload, "expected_revision_version": revision.lock_version + 1},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_attendance_completes_release_pinned_live_activity_without_global_requirement(
        self,
    ) -> None:
        (
            owner,
            organization,
            revision,
            module,
            _unit,
            _objective,
            _topic,
            _publication,
            release,
        ) = self.published_context()
        learner = self.member(
            owner, organization, RoleCode.LEARNER, "live-activity@example.test"
        )
        learner_membership = Membership.objects.get(
            organization=organization, user=learner
        )
        host = self.member(
            owner,
            organization,
            RoleCode.INSTRUCTOR,
            "live-activity-host@example.test",
        )
        host_membership = Membership.objects.get(organization=organization, user=host)
        period = create_academic_period(
            actor=owner,
            organization=organization,
            name="Periodo en vivo",
            slug="periodo-en-vivo",
            period_type="term",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
        )
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            academic_period=period,
            name="Grupo en vivo",
            staff=[
                {
                    "membership_id": host_membership.id,
                    "role": "lead_instructor",
                }
            ],
        )
        activity = CourseGroupActivity(
            course_group=cohort,
            academic_period=period,
            course_release=release,
            source_activity_id=uuid.uuid4(),
            source_module_id=module.id,
            activity_type="live_class",
            module_title=module.title,
            title="Clase sincrónica curricular",
            module_position=1,
            position=2,
            required=True,
            completion_policy={"method": "attendance"},
            availability_rules=[],
            binding_snapshot={
                "provider": "scheduling",
                "minimum_attended_occurrences": 1,
                "minimum_attendance_minutes": 1,
            },
            release_snapshot_digest=release.snapshot_digest,
        )
        activity.full_clean()
        activity.save()
        enrollment = enroll_member(
            actor=owner,
            organization=organization,
            course=revision.course,
            membership=learner_membership,
            release=release,
            cohort=cohort,
        )
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

        def record_attendance(series, *, suffix: str) -> None:
            session = (
                series.occurrences.select_related("live_session").get().live_session
            )
            session.status = LiveSessionStatus.LIVE
            session.actual_started_at = timezone.now()
            session.save(update_fields=("status", "actual_started_at", "updated_at"))
            created_at = int(timezone.now().timestamp())
            joined = {
                "id": str(uuid.uuid4()),
                "event": "participant_joined",
                "createdAt": str(created_at),
                "room": {"name": session.room_name, "sid": f"RM_{suffix}"},
                "participant": {
                    "identity": f"user:{learner.id}",
                    "sid": f"PA_{suffix}",
                    "attributes": {"lms.role": "student"},
                },
            }
            for payload in (
                joined,
                {
                    **joined,
                    "id": str(uuid.uuid4()),
                    "event": "participant_left",
                    "createdAt": str(created_at + 75),
                },
            ):
                body, token = signed_webhook(payload)
                receive_and_process_webhook(
                    body=body, authorization=token, gateway=gateway
                )

        supplemental = create_event_series(
            actor=owner,
            organization=organization,
            course=revision.course,
            course_group=cohort,
            course_group_activity=activity,
            host_membership=host_membership,
            title=f"{activity.title} · apoyo",
            description="",
            event_type=EventType.LIVE_CLASS,
            timezone_name="America/Bogota",
            first_starts_at=timezone.now() + timedelta(minutes=2),
            duration_minutes=60,
            contributes_to_activity_progress=False,
        )
        record_attendance(supplemental, suffix="supplemental")
        progress = ActivityProgress.objects.get(
            course_progress=enrollment.current_release_assignment.progress,
            group_activity=activity,
        )
        self.assertNotEqual(progress.status, "completed")

        primary = create_event_series(
            actor=owner,
            organization=organization,
            course=revision.course,
            course_group=cohort,
            course_group_activity=activity,
            host_membership=host_membership,
            title=activity.title,
            description="",
            event_type=EventType.LIVE_CLASS,
            timezone_name="America/Bogota",
            first_starts_at=timezone.now() + timedelta(minutes=3),
            duration_minutes=60,
        )
        record_attendance(primary, suffix="primary")
        progress.refresh_from_db()
        self.assertEqual(progress.status, "completed")
        self.assertEqual(progress.evidence["attendance_seconds"], 75)
        self.assertFalse(ExternalRequirementCompletion.objects.exists())

    def test_live_session_directory_includes_standalone_and_filters_course(
        self,
    ) -> None:
        context = self.scheduling_context()
        standalone = create_event_series(
            actor=context["owner"],
            organization=context["organization"],
            course=None,
            host_membership=context["series"].host_membership,
            participant_memberships=[context["learner_membership"]],
            title="Tutoría particular",
            description="Sesión independiente",
            event_type=EventType.LIVE_CLASS,
            timezone_name="America/Bogota",
            first_starts_at=timezone.now() + timedelta(hours=2),
            duration_minutes=45,
        )
        client = APIClient()
        client.force_authenticate(context["learner"])
        base = (
            f"/api/v1/organizations/{context['organization'].slug}"
            "/scheduling/live-sessions/"
        )

        listing = client.get(base, {"scope": "all"})
        self.assertEqual(listing.status_code, 200)
        by_title = {row["title"]: row for row in listing.json()}
        self.assertIsNone(by_title[standalone.title]["course"])
        self.assertIn(context["series"].title, by_title)

        filtered = client.get(
            base,
            {"course_slug": context["course"].slug, "scope": "all"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertTrue(filtered.json())
        self.assertTrue(
            all(
                row["course"]["slug"] == context["course"].slug
                for row in filtered.json()
            )
        )

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
        series = context["series"]
        series.counts_toward_progress = True
        series.attendance_threshold_minutes = 1
        series.full_clean()
        series.save(
            update_fields=(
                "counts_toward_progress",
                "attendance_threshold_minutes",
                "updated_at",
            )
        )
        register_live_session_requirement(
            actor=context["owner"],
            organization=context["organization"],
            course=context["course"],
            source_id=session.id,
            title=series.title,
        )
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
            body=body, authorization=f"Bearer {token}", gateway=gateway
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
        self.assertEqual(ExternalRequirementCompletion.objects.count(), 1)
        progress = context["enrollment"].current_release_assignment.progress
        progress.refresh_from_db()
        self.assertEqual(progress.total_required_activities, 1)
        self.assertEqual(progress.completed_required_activities, 1)

    def test_invalid_webhook_signature_is_rejected_by_endpoint(self) -> None:
        client = APIClient()
        response = client.post(
            "/api/v1/livekit/webhook/",
            data=b"{}",
            content_type="application/webhook+json",
            HTTP_AUTHORIZATION="not-a-token",
        )
        self.assertEqual(response.status_code, 401)
