import uuid
from datetime import date

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from domain.courses.choices import ActivityCompletionMethod, ActivityType
from domain.courses.models import CourseActivity
from domain.courses.services import create_activity, create_module
from domain.learning.models import CourseGroupActivity
from domain.learning.services import (
    create_academic_period,
    create_cohort,
    enroll_member,
)
from domain.organizations.choices import RoleCode
from domain.organizations.models import Membership
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)

from ..api.serializers import AttemptResultSerializer
from ..choices import ResponseStatus
from ..gradebooks import create_gradebook
from ..models import AnalyticsRefreshJob, AssessmentAnalyticsSnapshot, RegradeJob
from ..services import (
    activate_delivery,
    assign_delivery,
    create_delivery,
    save_response,
    start_attempt,
    submit_attempt,
)
from .support import AssessmentFixtureMixin


class AssessmentApiSecurityTests(AssessmentFixtureMixin, TestCase):
    def test_approved_version_creates_and_binds_curricular_activity_atomically(
        self,
    ) -> None:
        context = self.assessment_context()
        revision = context["course_revision"]
        module, revision = create_module(
            actor=context["owner"],
            organization=context["organization"],
            revision=revision,
            expected_version=revision.lock_version,
            title="Evaluaciones",
        )
        client = APIClient()
        client.force_authenticate(user=context["owner"])
        url = (
            f"/api/v1/organizations/{context['organization'].slug}/assessments/"
            "course-activities/"
        )
        payload = {
            "assessment_version_id": str(context["assessment_version"].id),
            "expected_revision_version": revision.lock_version,
            "module_id": str(module.id),
            "required": True,
        }
        created = client.post(url, payload, format="json")
        self.assertEqual(created.status_code, 201)
        activity = CourseActivity.objects.get(pk=created.data["activity_id"])
        version = context["assessment_version"]
        self.assertEqual(activity.title, version.title)
        self.assertEqual(
            activity.estimated_duration_minutes, version.time_limit_minutes
        )
        self.assertEqual(activity.minimum_grade_basis_points, version.pass_basis_points)
        self.assertSetEqual(
            set(
                activity.objective_alignments.values_list(
                    "learning_objective_id", flat=True
                )
            ),
            set(
                version.source_revision.objective_links.values_list(
                    "objective_id", flat=True
                )
            ),
        )
        self.assertEqual(
            created.data["revision_lock_version"], revision.lock_version + 3
        )
        before = CourseActivity.objects.count()
        conflict = client.post(url, payload, format="json")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(CourseActivity.objects.count(), before)

    def test_incompatible_assessment_is_rejected_before_creating_activity(
        self,
    ) -> None:
        context = self.assessment_context()
        revision = context["course_revision"]
        module, revision = create_module(
            actor=context["owner"],
            organization=context["organization"],
            revision=revision,
            expected_version=revision.lock_version,
            title="Evaluaciones",
        )
        revision.objective_alignments.all().delete()
        client = APIClient()
        client.force_authenticate(user=context["owner"])
        before = CourseActivity.objects.count()
        response = client.post(
            f"/api/v1/organizations/{context['organization'].slug}/assessments/course-activities/",
            {
                "assessment_version_id": str(context["assessment_version"].id),
                "expected_revision_version": revision.lock_version,
                "module_id": str(module.id),
                "required": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CourseActivity.objects.count(), before)

    def test_approved_assessment_version_binds_once_to_curricular_activity(
        self,
    ) -> None:
        context = self.assessment_context()
        revision = context["course_revision"]
        module, revision = create_module(
            actor=context["owner"],
            organization=context["organization"],
            revision=revision,
            expected_version=revision.lock_version,
            title="Evaluaciones",
        )
        activity, revision = create_activity(
            actor=context["owner"],
            organization=context["organization"],
            module=module,
            expected_version=revision.lock_version,
            activity_type=ActivityType.ASSESSMENT,
            title="Diagnóstico",
            completion_method=ActivityCompletionMethod.PASS,
            minimum_grade_basis_points=6000,
        )
        client = APIClient()
        client.force_authenticate(user=context["owner"])
        url = (
            f"/api/v1/organizations/{context['organization'].slug}/assessments/"
            f"course-activities/{activity.id}/binding/"
        )
        payload = {
            "assessment_version_id": str(context["assessment_version"].id),
            "expected_revision_version": revision.lock_version,
        }
        created = client.post(url, payload, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["activity_id"], str(activity.id))
        self.assertEqual(
            created.data["revision_lock_version"], revision.lock_version + 1
        )
        duplicate = client.post(
            url,
            {**payload, "expected_revision_version": revision.lock_version + 1},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_instructor_delivery_and_gradebook_scope_is_limited_to_assigned_group(
        self,
    ) -> None:
        context = self.assessment_context(with_learning=True)
        instructor = self.member(
            context["owner"],
            context["organization"],
            RoleCode.INSTRUCTOR,
            "scoped-instructor@example.test",
        )
        instructor_membership = Membership.objects.get(
            organization=context["organization"], user=instructor
        )
        period = create_academic_period(
            actor=context["owner"],
            organization=context["organization"],
            name="Periodo 1",
            slug="periodo-1",
            period_type="term",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 6, 30),
        )
        assigned_group = create_cohort(
            actor=context["owner"],
            organization=context["organization"],
            course=context["release"].course,
            release=context["release"],
            academic_period=period,
            name="Grupo asignado",
            slug="grupo-asignado",
            staff=[
                {
                    "membership_id": instructor_membership.id,
                    "role": "instructor",
                }
            ],
        )
        foreign_group = create_cohort(
            actor=context["owner"],
            organization=context["organization"],
            course=context["release"].course,
            release=context["release"],
            academic_period=period,
            name="Grupo ajeno",
            slug="grupo-ajeno",
        )

        def assessment_activity(group, position: int) -> CourseGroupActivity:
            row = CourseGroupActivity(
                course_group=group,
                academic_period=period,
                course_release=context["release"],
                source_activity_id=uuid.uuid4(),
                source_module_id=uuid.uuid4(),
                activity_type="assessment",
                module_title="Evaluaciones",
                title="Diagnóstico",
                module_position=2,
                position=position,
                required=True,
                completion_policy={"method": "pass"},
                availability_rules=[],
                binding_snapshot={
                    "provider": "assessments",
                    "assessment_version_id": str(context["assessment_version"].id),
                },
                release_snapshot_digest=context["release"].snapshot_digest,
            )
            row.full_clean()
            row.save()
            return row

        assigned_activity = assessment_activity(assigned_group, 1)
        foreign_activity = assessment_activity(foreign_group, 1)
        assigned_delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega asignada",
            course_release=context["release"],
            course_group_activity=assigned_activity,
        )
        foreign_delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega ajena",
            course_release=context["release"],
            course_group_activity=foreign_activity,
        )
        assigned_gradebook = create_gradebook(
            actor=context["owner"],
            organization=context["organization"],
            course_release=context["release"],
            course_group=assigned_group,
            academic_period=period,
        )
        foreign_gradebook = create_gradebook(
            actor=context["owner"],
            organization=context["organization"],
            course_release=context["release"],
            course_group=foreign_group,
            academic_period=period,
        )
        client = APIClient()
        client.force_authenticate(instructor)
        base = f"/api/v1/organizations/{context['organization'].slug}/assessments"
        self.assertEqual(client.get(f"{base}/").status_code, 403)
        options = client.get(f"{base}/approved-version-options/")
        self.assertEqual(options.status_code, 200)
        self.assertEqual(
            {row["id"] for row in options.json()},
            {str(context["assessment_version"].id)},
        )
        deliveries = client.get(f"{base}/deliveries/")
        self.assertEqual(deliveries.status_code, 200)
        payload = deliveries.json()
        rows = payload["results"] if isinstance(payload, dict) else payload
        self.assertEqual({row["id"] for row in rows}, {str(assigned_delivery.id)})
        self.assertEqual(
            client.get(f"{base}/deliveries/{foreign_delivery.id}/").status_code,
            404,
        )
        gradebooks = client.get(f"{base}/gradebooks/")
        self.assertEqual(gradebooks.status_code, 200)
        self.assertEqual(
            {row["id"] for row in gradebooks.json()}, {str(assigned_gradebook.id)}
        )
        self.assertEqual(
            client.get(f"{base}/gradebooks/{foreign_gradebook.id}/").status_code,
            404,
        )

        def attempt_for_group(group, delivery, suffix: str):
            learner = self.member(
                context["owner"],
                context["organization"],
                RoleCode.LEARNER,
                f"group-learner-{suffix}@example.test",
            )
            membership = Membership.objects.get(
                organization=context["organization"], user=learner
            )
            enrollment = enroll_member(
                actor=context["owner"],
                organization=context["organization"],
                course=context["release"].course,
                membership=membership,
                release=context["release"],
                cohort=group,
            )
            delivery = activate_delivery(
                actor=context["owner"],
                delivery=delivery,
                expected_version=delivery.lock_version,
            )
            assignment = assign_delivery(
                actor=context["owner"],
                delivery=delivery,
                release_assignment=enrollment.current_release_assignment,
            )
            attempt = start_attempt(actor=learner, assignment=assignment)
            attempt, response = save_response(
                actor=learner,
                attempt=attempt,
                attempt_item=attempt.items.get(),
                expected_version=attempt.lock_version,
                payload={
                    "schema_version": 1,
                    "type": "single_choice",
                    "value": "b",
                },
            )
            response.status = ResponseStatus.PENDING_MANUAL
            response.save(update_fields=("status", "updated_at"))
            return attempt, response

        assigned_attempt, assigned_response = attempt_for_group(
            assigned_group, assigned_delivery, "assigned"
        )
        foreign_attempt, foreign_response = attempt_for_group(
            foreign_group, foreign_delivery, "foreign"
        )
        results = client.get(f"{base}/results/")
        self.assertEqual(results.status_code, 200)
        result_rows = results.json()["results"]
        self.assertEqual({row["id"] for row in result_rows}, {str(assigned_attempt.id)})
        manual = client.get(f"{base}/manual-grading/")
        self.assertEqual(manual.status_code, 200)
        self.assertEqual(
            {row["response_id"] for row in manual.json()},
            {str(assigned_response.id)},
        )
        self.assertEqual(
            client.post(
                f"{base}/manual-grading/{foreign_response.id}/",
                {"score": "1.000", "feedback": "No autorizado"},
                format="json",
            ).status_code,
            404,
        )
        self.assertNotEqual(assigned_attempt.id, foreign_attempt.id)

        grading_revision = context["assessment_version"].grading_policy.current_revision
        self.assertIsNotNone(grading_revision)
        assigned_regrade = RegradeJob.objects.create(
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            grading_revision=grading_revision,
            delivery=assigned_delivery,
            reason="Recalificación del grupo asignado.",
            task_id=uuid.uuid4(),
            created_by=context["owner"],
        )
        foreign_regrade = RegradeJob.objects.create(
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            grading_revision=grading_revision,
            delivery=foreign_delivery,
            reason="Recalificación del grupo ajeno.",
            task_id=uuid.uuid4(),
            created_by=context["owner"],
        )
        for delivery in (assigned_delivery, foreign_delivery):
            AssessmentAnalyticsSnapshot.objects.create(
                assessment_version=context["assessment_version"],
                grading_revision=grading_revision,
                delivery=delivery,
                sample_size=1,
                mean_percent_basis_points=10_000,
                created_by=context["owner"],
            )
        assigned_analytics_job = AnalyticsRefreshJob.objects.create(
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            grading_revision=grading_revision,
            delivery=assigned_delivery,
            task_id=uuid.uuid4(),
            created_by=context["owner"],
        )
        foreign_analytics_job = AnalyticsRefreshJob.objects.create(
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            grading_revision=grading_revision,
            delivery=foreign_delivery,
            task_id=uuid.uuid4(),
            created_by=context["owner"],
        )
        regrades = client.get(f"{base}/regrade-jobs/")
        self.assertEqual(regrades.status_code, 200)
        self.assertEqual(
            {row["id"] for row in regrades.json()}, {str(assigned_regrade.id)}
        )
        self.assertEqual(
            client.get(f"{base}/regrade-jobs/{foreign_regrade.id}/").status_code,
            404,
        )
        analytics_url = (
            f"{base}/analytics/assessments/{context['assessment_version'].id}/"
        )
        self.assertEqual(
            client.get(
                analytics_url, {"delivery": str(assigned_delivery.id)}
            ).status_code,
            200,
        )
        self.assertEqual(
            client.get(
                analytics_url, {"delivery": str(foreign_delivery.id)}
            ).status_code,
            404,
        )
        self.assertEqual(
            client.get(
                f"{base}/analytics/jobs/{assigned_analytics_job.id}/"
            ).status_code,
            200,
        )
        self.assertEqual(
            client.get(
                f"{base}/analytics/jobs/{foreign_analytics_job.id}/"
            ).status_code,
            404,
        )
        advanced_payload = {
            "assessment_version_id": str(context["assessment_version"].id),
            "grading_revision_id": str(grading_revision.id),
            "delivery_id": str(foreign_delivery.id),
        }
        self.assertEqual(
            client.post(
                f"{base}/analytics/refresh/", advanced_payload, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            client.post(
                f"{base}/regrade-jobs/",
                {
                    **advanced_payload,
                    "reason": "Intento sobre grupo ajeno.",
                    "preserve_manual_grades": True,
                },
                format="json",
            ).status_code,
            404,
        )

    def test_administrator_can_read_revision_metadata_for_analytics(self) -> None:
        context = self.assessment_context(with_learning=True)
        administrator = self.member(
            context["owner"],
            context["organization"],
            RoleCode.ADMINISTRATOR,
            "analytics-administrator@example.test",
        )
        client = APIClient()
        client.force_authenticate(administrator)
        response = client.get(
            "/api/v1/organizations/"
            f"{context['organization'].slug}/assessments/scoring-policies/"
            f"{context['assessment_version'].id}/revisions/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json())
        self.assertNotIn("grading_payload", response.content.decode("utf-8"))

    def test_learner_attempt_payload_never_contains_grading_material(self) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Diagnóstico seguro",
            course_release=context["release"],
            migration_review_required=True,
        )
        delivery = activate_delivery(
            actor=context["owner"],
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=context["owner"],
            delivery=delivery,
            release_assignment=context["enrollment"].current_release_assignment,
        )
        attempt = start_attempt(actor=context["learner"], assignment=assignment)
        client = APIClient()
        client.force_authenticate(context["learner"])
        response = client.get(
            f"/api/v1/organizations/{context['organization'].slug}/assessments/attempts/{attempt.id}/"
        )
        self.assertEqual(response.status_code, 200)
        serialized = response.content.decode("utf-8")
        for forbidden in (
            "grading",
            "correct_option_ids",
            "correct_value",
            "accepted_answers",
            "correct_order",
            "correct_pairs",
            "rubric",
            "seed",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_learner_cannot_open_authoring_bank_endpoint(self) -> None:
        context = self.assessment_context(with_learning=True)
        client = APIClient()
        client.force_authenticate(context["learner"])
        response = client.get(
            f"/api/v1/organizations/{context['organization'].slug}/assessments/question-banks/"
        )
        self.assertEqual(response.status_code, 403)

    def test_approved_question_options_are_batched_and_tenant_scoped(self) -> None:
        context = self.assessment_context(with_learning=True)
        client = APIClient()
        client.force_authenticate(context["owner"])
        response = client.get(
            f"/api/v1/organizations/{context['organization'].slug}/assessments/approved-question-version-options/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(context["question_version"].id))
        self.assertEqual(response.data[0]["bank_name"], context["bank"].name)
        self.assertEqual(response.data[0]["code"], context["question"].code)

    def test_feedback_modes_expose_none_score_only_or_full_after_grading(
        self,
    ) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Feedback determinista",
            course_release=context["release"],
            migration_review_required=True,
        )
        delivery = activate_delivery(
            actor=context["owner"],
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=context["owner"],
            delivery=delivery,
            release_assignment=context["enrollment"].current_release_assignment,
        )
        attempt = start_attempt(actor=context["learner"], assignment=assignment)
        attempt, _ = save_response(
            actor=context["learner"],
            attempt=attempt,
            attempt_item=attempt.items.get(),
            expected_version=attempt.lock_version,
            payload={
                "schema_version": 1,
                "type": "single_choice",
                "value": "b",
            },
        )
        attempt = submit_attempt(
            actor=context["learner"],
            attempt=attempt,
            expected_version=attempt.lock_version,
        )
        attempt = (
            type(attempt)
            .objects.prefetch_related("items__response__manual_decisions")
            .get(pk=attempt.pk)
        )
        attempt.assessment_version.feedback_mode = "none"
        self.assertEqual(AttemptResultSerializer(attempt).data["feedback"], [])
        attempt.assessment_version.feedback_mode = "score_only"
        score_only = AttemptResultSerializer(attempt).data["feedback"]
        self.assertEqual(len(score_only), 1)
        self.assertNotIn("message", score_only[0])
        attempt.assessment_version.feedback_mode = "full_after_grading"
        full = AttemptResultSerializer(attempt).data["feedback"]
        self.assertEqual(full[0]["message"], "Revisa el concepto evaluado.")

    def test_cross_organization_identifiers_fail_closed_for_every_surface(
        self,
    ) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Entrega protegida",
            course_release=context["release"],
            migration_review_required=True,
        )
        delivery = activate_delivery(
            actor=context["owner"],
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=context["owner"],
            delivery=delivery,
            release_assignment=context["enrollment"].current_release_assignment,
        )
        attempt = start_attempt(actor=context["learner"], assignment=assignment)
        attempt = submit_attempt(
            actor=context["learner"],
            attempt=attempt,
            expected_version=attempt.lock_version,
        )
        outsider = get_user_model().objects.create_user(
            email="assessment-outsider@example.test",
            password="AssessmentOutsiderPassword!42",
        )
        EmailAddress.objects.create(
            user=outsider, email=outsider.email, primary=True, verified=True
        )
        other = create_organization_with_owner(
            actor=outsider, name="Otra institución", slug="otra-institucion"
        )
        cross_scope_actor = get_user_model().objects.create_user(
            email="assessment-cross-scope@example.test",
            password="AssessmentCrossScopePassword!42",
        )
        EmailAddress.objects.create(
            user=cross_scope_actor,
            email=cross_scope_actor.email,
            primary=True,
            verified=True,
        )
        add_existing_member_with_roles(
            actor=outsider,
            organization=other,
            user=cross_scope_actor,
            roles={
                RoleCode.ADMINISTRATOR,
                RoleCode.AUTHOR,
                RoleCode.LEARNER,
            },
        )
        client = APIClient()
        client.force_authenticate(cross_scope_actor)
        paths = (
            (
                "post",
                f"/api/v1/organizations/{other.slug}/assessments/question-banks/{context['bank'].id}/archive/",
                {"expected_version": context["bank"].lock_version},
            ),
            (
                "get",
                f"/api/v1/organizations/{other.slug}/assessments/question-banks/{context['bank'].id}/questions/{context['question'].id}/revisions/{context['question_revision'].id}/",
                None,
            ),
            (
                "get",
                f"/api/v1/organizations/{other.slug}/assessments/{context['assessment'].slug}/",
                None,
            ),
            (
                "get",
                f"/api/v1/organizations/{other.slug}/assessments/deliveries/{delivery.id}/",
                None,
            ),
            (
                "get",
                f"/api/v1/organizations/{other.slug}/assessments/attempts/{attempt.id}/",
                None,
            ),
            (
                "get",
                f"/api/v1/organizations/{other.slug}/assessments/attempts/{attempt.id}/result/",
                None,
            ),
        )
        for method, path, payload in paths:
            with self.subTest(path=path):
                response = getattr(client, method)(path, payload, format="json")
                self.assertEqual(response.status_code, 404)

    def test_mass_assignment_field_is_rejected(self) -> None:
        context = self.assessment_context()
        client = APIClient()
        client.force_authenticate(context["owner"])
        revision = context["assessment_revision"]
        response = client.patch(
            f"/api/v1/organizations/{context['organization'].slug}/assessments/{context['assessment'].slug}/revisions/{revision.id}/",
            {
                "expected_version": revision.lock_version,
                "title": "Intento de escalamiento",
                "status": "approved",
                "created_by_id": str(context["owner"].id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.data)
        self.assertIn("created_by_id", response.data)
