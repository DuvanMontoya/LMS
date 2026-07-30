from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from domain.learning.services import create_cohort, enroll_member
from domain.organizations.models import Membership

from .support import LearningFixtureMixin


class LearningApiTests(LearningFixtureMixin, TestCase):
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
            (admin, f"{base}/enrollments/{cohort_enrollment.id}/progress/", 6),
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
