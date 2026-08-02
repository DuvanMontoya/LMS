import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from domain.learning.choices import (
    AcademicGroupLevel,
    AcademicGroupRole,
    AcademicPeriodType,
    CohortStaffRole,
)
from domain.learning.exceptions import LearningPermissionDenied
from domain.learning.models import CourseGroupActivity
from domain.learning.services import (
    create_academic_group,
    create_academic_period,
    create_cohort,
    enroll_member,
    replace_academic_group_roster,
    replace_cohort_staff,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership

from .support import LearningFixtureMixin


class LearningApiTests(LearningFixtureMixin, TestCase):
    def test_course_group_activity_options_are_scoped_to_assigned_staff(self) -> None:
        (
            owner,
            _learner,
            organization,
            _learner_membership,
            revision,
            module,
            _unit,
            _publication,
            release,
            _enrollment,
        ) = self.learning_context()
        period = create_academic_period(
            actor=owner,
            organization=organization,
            name="Periodo de opciones",
            slug="periodo-opciones",
            period_type=AcademicPeriodType.TERM,
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=90),
        )
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            academic_period=period,
            name="Grupo asignado",
        )
        instructor = self.member(
            owner, organization, RoleCode.INSTRUCTOR, "group-teacher@example.test"
        )
        other = self.member(
            owner, organization, RoleCode.INSTRUCTOR, "other-group@example.test"
        )
        instructor_membership = Membership.objects.get(
            organization=organization, user=instructor
        )
        cohort = replace_cohort_staff(
            actor=owner,
            cohort=cohort,
            expected_cohort_version=cohort.lock_version,
            staff=[
                {
                    "membership_id": instructor_membership.id,
                    "role": CohortStaffRole.INSTRUCTOR,
                }
            ],
        )
        activity = CourseGroupActivity.objects.create(
            course_group=cohort,
            academic_period=period,
            course_release=release,
            source_activity_id=uuid.uuid4(),
            source_module_id=module.id,
            activity_type="live_class",
            module_title=module.title,
            title="Clase curricular del grupo",
            module_position=1,
            position=2,
            required=True,
            completion_policy={"method": "attendance"},
            availability_rules=[],
            binding_snapshot={"minimum_attended_occurrences": 1},
            release_snapshot_digest=release.snapshot_digest,
        )
        url = (
            f"/api/v1/organizations/{organization.slug}/learning/"
            "course-group-activities/?activity_type=live_class"
        )
        instructor_client = APIClient()
        instructor_client.force_authenticate(instructor)
        listed = instructor_client.get(url)
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual([row["id"] for row in listed.data], [str(activity.id)])
        other_client = APIClient()
        other_client.force_authenticate(other)
        self.assertEqual(other_client.get(url).data, [])

    def test_course_group_staff_rejects_non_instructor_memberships(self) -> None:
        (
            owner,
            _learner,
            organization,
            learner_membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            _enrollment,
        ) = self.learning_context()
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            migration_review_required=True,
            name="Grupo con equipo validado",
        )
        with self.assertRaises(LearningPermissionDenied):
            replace_cohort_staff(
                actor=owner,
                cohort=cohort,
                expected_cohort_version=cohort.lock_version,
                staff=[
                    {
                        "membership_id": learner_membership.id,
                        "role": CohortStaffRole.ASSISTANT,
                    }
                ],
            )

    def test_group_learner_uses_unified_activity_outline_and_detail(self) -> None:
        (
            owner,
            _learner,
            organization,
            _membership,
            revision,
            _module,
            unit,
            _publication,
            release,
            _enrollment,
        ) = self.learning_context()
        period = create_academic_period(
            actor=owner,
            organization=organization,
            name="Semestre uno",
            slug="semestre-uno",
            period_type=AcademicPeriodType.SEMESTER,
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=120),
        )
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            academic_period=period,
            name="Grupo con actividades",
        )
        learner = get_user_model().objects.create_user(
            email="activity-learner@example.test",
            password="StrongLearningPassword!42",
        )
        membership = Membership.objects.create(
            organization=organization,
            user=learner,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        enrollment = enroll_member(
            actor=owner,
            organization=organization,
            course=revision.course,
            membership=membership,
            cohort=cohort,
        )
        client = APIClient()
        client.force_authenticate(learner)
        base = (
            f"/api/v1/organizations/{organization.slug}/learning/me/"
            f"enrollments/{enrollment.id}"
        )
        outline = client.get(f"{base}/outline/")
        self.assertEqual(outline.status_code, 200, outline.data)
        activities = outline.data["modules"][0]["activities"]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["type"], "lesson")
        self.assertEqual(activities[0]["source_activity_id"], unit.id)
        self.assertIn("/actividades/", activities[0]["href"])
        detail = client.get(f"{base}/activities/{activities[0]['id']}/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["activity"]["type"], "lesson")
        self.assertEqual(detail.data["lesson"]["unit_id"], unit.id)
        self.assertEqual(detail.data["navigation"]["total"], 1)

    def test_new_course_group_requires_an_academic_period(self) -> None:
        (
            owner,
            _learner,
            organization,
            _membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            _enrollment,
        ) = self.learning_context()
        client = APIClient()
        client.force_authenticate(owner)
        base = f"/api/v1/organizations/{organization.slug}/learning"
        payload = {
            "course_slug": revision.course.slug,
            "release_number": release.number,
            "name": "Grupo 2026",
        }
        missing = client.post(f"{base}/cohorts/", payload, format="json")
        self.assertEqual(missing.status_code, 400, missing.data)
        self.assertIn("academic_period_id", missing.data)

        period = client.post(
            f"{base}/academic-periods/",
            {
                "name": "Año académico 2026",
                "slug": "ano-2026",
                "period_type": "school_year",
                "starts_on": "2026-01-01",
                "ends_on": "2026-12-31",
            },
            format="json",
        )
        self.assertEqual(period.status_code, 201, period.data)
        payload["academic_period_id"] = period.data["id"]
        created = client.post(f"{base}/cohorts/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["academic_period_id"], period.data["id"])
        self.assertFalse(created.data["migration_review_required"])

    def test_roster_read_is_searchable_and_stale_write_returns_conflict(self) -> None:
        (
            owner,
            _learner,
            organization,
            membership,
            _revision,
            _module,
            _unit,
            _publication,
            _release,
            _enrollment,
        ) = self.learning_context()
        group = create_academic_group(
            actor=owner,
            organization=organization,
            name="Undécimo para API",
            academic_year=2026,
            level=AcademicGroupLevel.SECONDARY_11,
        )
        group = replace_academic_group_roster(
            actor=owner,
            group=group,
            expected_group_version=group.lock_version,
            members=[
                {"membership_id": membership.id, "role": AcademicGroupRole.LEARNER}
            ],
        )
        client = APIClient()
        client.force_authenticate(owner)
        base = f"/api/v1/organizations/{organization.slug}/learning"

        roster = client.get(
            f"{base}/academic-groups/{group.id}/roster/",
            {"search": membership.user.email, "page_size": 1},
        )
        self.assertEqual(roster.status_code, 200)
        self.assertEqual(roster.json()["count"], 1)
        self.assertEqual(roster.json()["results"][0]["email"], membership.user.email)

        stale = client.put(
            f"{base}/academic-groups/{group.id}/roster/",
            {"expected_group_version": group.lock_version - 1, "members": []},
            format="json",
        )
        self.assertEqual(stale.status_code, 409)

    def test_admin_and_student_surfaces_enforce_identity_scope(self) -> None:
        (
            owner,
            learner,
            organization,
            _membership,
            _revision,
            _module,
            unit,
            _publication,
            _release,
            enrollment,
        ) = self.learning_context()
        admin = APIClient()
        admin.force_authenticate(owner)
        base = f"/api/v1/organizations/{organization.slug}/learning"
        response = admin.get(f"{base}/enrollments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        student = APIClient()
        student.force_authenticate(learner)
        response = student.get(f"{base}/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["enrollment_id"], str(enrollment.id))
        outline = student.get(f"{base}/me/enrollments/{enrollment.id}/outline/")
        self.assertEqual(outline.status_code, 200)
        unit_response = student.get(
            f"{base}/me/enrollments/{enrollment.id}/units/{unit.id}/"
        )
        self.assertEqual(unit_response.status_code, 200)
        self.assertIn("content", unit_response.json())

    def test_admin_lists_accept_explicit_created_at_ordering(self) -> None:
        (
            owner,
            _learner,
            organization,
            _membership,
            revision,
            _module,
            _unit,
            _publication,
            release,
            _enrollment,
        ) = self.learning_context()
        create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            migration_review_required=True,
            name="Cohorte para ordenar",
        )
        client = APIClient()
        client.force_authenticate(owner)
        base = f"/api/v1/organizations/{organization.slug}/learning"

        for resource in ("cohorts", "enrollments"):
            for ordering in ("created_at", "-created_at"):
                with self.subTest(resource=resource, ordering=ordering):
                    response = client.get(f"{base}/{resource}/", {"ordering": ordering})
                    self.assertEqual(response.status_code, 200)

    def test_foreign_enrollment_and_mass_assignment_fail_closed(self) -> None:
        (
            _owner,
            learner,
            organization,
            _membership,
            _revision,
            _module,
            _unit,
            _publication,
            _release,
            enrollment,
        ) = self.learning_context()
        outsider = type(learner).objects.create_user(
            email="learning-outsider@example.test", password="OutsiderPassword!42"
        )
        client = APIClient()
        client.force_authenticate(outsider)
        base = f"/api/v1/organizations/{organization.slug}/learning"
        response = client.get(f"{base}/me/enrollments/{enrollment.id}/")
        self.assertEqual(response.status_code, 404)

    def test_read_query_budgets_cover_student_and_admin_surfaces(self) -> None:
        (
            owner,
            learner,
            organization,
            _membership,
            revision,
            _module,
            unit,
            _publication,
            release,
            enrollment,
        ) = self.learning_context()
        cohort = create_cohort(
            actor=owner,
            organization=organization,
            course=revision.course,
            release=release,
            migration_review_required=True,
            name="Cohorte para presupuesto",
        )
        cohort_user = get_user_model().objects.create_user(
            email="query-budget@example.test", password="StrongLearningPassword!42"
        )
        cohort_membership = Membership.objects.create(
            organization=organization,
            user=cohort_user,
            status_changed_by=owner,
            status_changed_at=timezone.now(),
        )
        cohort_enrollment = enroll_member(
            actor=owner,
            organization=organization,
            course=revision.course,
            membership=cohort_membership,
            cohort=cohort,
        )
        base = f"/api/v1/organizations/{organization.slug}/learning"
        student = APIClient()
        student.force_authenticate(learner)
        admin = APIClient()
        admin.force_authenticate(owner)
        calls = [
            (student, f"{base}/me/", 6),
            (student, f"{base}/me/enrollments/{enrollment.id}/outline/", 8),
            (student, f"{base}/me/enrollments/{enrollment.id}/units/{unit.id}/", 8),
            (admin, f"{base}/enrollments/", 8),
            (admin, f"{base}/cohorts/{cohort.id}/progress/", 10),
            (admin, f"{base}/enrollments/{cohort_enrollment.id}/progress/", 7),
        ]
        for client, path, budget in calls:
            with self.subTest(path=path), CaptureQueriesContext(connection) as queries:
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
            self.assertLessEqual(
                len(queries),
                budget,
                f"{path} usó {len(queries)} queries; presupuesto {budget}.",
            )
