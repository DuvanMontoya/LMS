from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from domain.organizations.services import create_organization_with_owner

from ..api.serializers import AttemptResultSerializer
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
    def test_learner_attempt_payload_never_contains_grading_material(self) -> None:
        context = self.assessment_context(with_learning=True)
        delivery = create_delivery(
            actor=context["owner"],
            organization=context["organization"],
            assessment_version=context["assessment_version"],
            name="Diagnóstico seguro",
            course_release=context["release"],
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
        client = APIClient()
        client.force_authenticate(outsider)
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
