# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.assessments.choices import AuthoringStatus
from domain.assessments.grading import create_scoring_correction
from domain.assessments.models import QuestionBank, QuestionVersion
from domain.assessments.services import (
    activate_delivery,
    add_assessment_item,
    add_assessment_section,
    assign_delivery,
    create_assessment,
    create_assessment_pool,
    create_delivery,
    create_question,
    create_question_bank,
    replace_assessment_objectives,
    transition_assessment_revision,
    transition_question_revision,
)
from domain.catalog.models import LearningObjective
from domain.courses.models import Course
from domain.identity.models import User
from domain.learning.models import CourseEnrollment
from domain.organizations.models import Organization
from domain.publishing.models import CoursePublication

from .bootstrap_demo_assessments import demo_question_definition


class Command(BaseCommand):
    help = "Crea el fixture avanzado efímero para assessment phase 14."

    def handle(self, *args: object, **options: object) -> None:
        if settings.SETTINGS_MODULE != "config.settings.e2e":
            raise CommandError("Este comando sólo puede ejecutarse con settings E2E.")
        with transaction.atomic():
            self._bootstrap()

    def _approve_question(
        self,
        *,
        owner: User,
        bank: QuestionBank,
        code: str,
        question_type: str,
        index: int,
    ) -> QuestionVersion:
        _, revision = create_question(
            actor=owner,
            bank=bank,
            code=code,
            question_type=question_type,
            definition=demo_question_definition(question_type, index),
        )
        revision, _ = transition_question_revision(
            actor=owner,
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        _, version = transition_question_revision(
            actor=owner,
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        if version is None:
            raise AssertionError("La aprobación debe materializar versión.")
        return version

    def _bootstrap(self) -> None:
        organization = Organization.objects.get(slug="organizacion-a")
        owner = User.objects.get(email="owner@organizations.e2e.test")
        course = Course.objects.get(
            organization=organization, slug="publicacion-inmutable-e2e"
        )
        release = CoursePublication.objects.get(course=course).current_release
        enrollment = CourseEnrollment.objects.get(
            membership__organization=organization,
            membership__user__email="learner@organizations.e2e.test",
            course=course,
        )
        objective = (
            LearningObjective.objects.filter(
                subject__discipline__area__organization=organization,
                status="active",
            )
            .order_by("code")
            .first()
        )
        if (
            release is None
            or objective is None
            or enrollment.current_release_assignment is None
        ):
            raise CommandError("Faltan release, objetivo o matrícula E2E.")
        bank = create_question_bank(
            actor=owner,
            organization=organization,
            name="Banco E2E avanzado",
            slug="banco-assessments-avanzado-e2e",
        )
        fixed_types = (
            "multiple_choice",
            "numeric",
            "ordering",
            "matching",
            "mathematical_expression",
        )
        fixed_versions = [
            self._approve_question(
                owner=owner,
                bank=bank,
                code=f"ADV-E2E-{index:03d}",
                question_type=question_type,
                index=200 + index,
            )
            for index, question_type in enumerate(fixed_types, start=1)
        ]
        pool_versions = [
            self._approve_question(
                owner=owner,
                bank=bank,
                code=f"ADV-POOL-{index:03d}",
                question_type="single_choice",
                index=300 + index,
            )
            for index in range(1, 21)
        ]
        assessment, revision = create_assessment(
            actor=owner,
            organization=organization,
            slug="assessment-avanzado-e2e",
            title="Assessment avanzado E2E",
            description="MathJSON, crédito parcial y pool 5/20.",
            instructions="Responde y envía para calificación asíncrona.",
            time_limit_minutes=30,
            attempt_limit=3,
            pass_basis_points=5000,
        )
        revision = replace_assessment_objectives(
            actor=owner,
            revision=revision,
            expected_version=revision.lock_version,
            objectives=[objective],
        )
        revision, section = add_assessment_section(
            actor=owner,
            revision=revision,
            expected_version=revision.lock_version,
            title="Scoring avanzado",
        )
        for version in fixed_versions:
            revision, _ = add_assessment_item(
                actor=owner,
                revision=revision,
                expected_version=revision.lock_version,
                section=section,
                question_version=version,
                points=Decimal("1.000"),
                required=True,
                objectives=[objective],
            )
        revision, _ = create_assessment_pool(
            actor=owner,
            revision=revision,
            expected_version=revision.lock_version,
            title="Pool 5 de 20",
            instructions="Selección aleatoria sin reemplazo.",
            selection_count=5,
            points_per_item=Decimal("1.000"),
            shuffle_selected=True,
            question_versions=pool_versions,
        )
        revision, _ = transition_assessment_revision(
            actor=owner,
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        _, version = transition_assessment_revision(
            actor=owner,
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        if version is None:
            raise AssertionError("La aprobación debe materializar versión.")
        policy = version.grading_policy
        current = policy.current_revision
        if current is None:
            raise AssertionError("La versión debe tener scoring original.")
        overrides: dict[str, dict[str, object]] = {}
        for item in current.grading_snapshot["items"]:
            question_type = item["question_type"]
            grading_payload = dict(item["grading_payload"])
            if question_type == "multiple_choice":
                overrides[item["source_id"]] = {
                    "scoring_policy": "proportional_with_penalty",
                    "grading_payload": grading_payload,
                }
            elif question_type == "numeric":
                overrides[item["source_id"]] = {
                    "scoring_policy": "banded_tolerance",
                    "grading_payload": {
                        "correct_value": grading_payload["correct_value"],
                        "full_tolerance": grading_payload["tolerance"],
                        "partial_tolerance": "0.5",
                        "partial_credit_basis_points": 5000,
                    },
                }
            elif question_type == "ordering":
                overrides[item["source_id"]] = {
                    "scoring_policy": "position_fraction",
                    "grading_payload": grading_payload,
                }
            elif question_type == "matching":
                overrides[item["source_id"]] = {
                    "scoring_policy": "per_pair",
                    "grading_payload": grading_payload,
                }
        correction = create_scoring_correction(
            actor=owner,
            assessment_version=version,
            expected_policy_version=policy.lock_version,
            reason="Crédito parcial E2E aprobado.",
            item_overrides=overrides,
        )
        delivery = create_delivery(
            actor=owner,
            organization=organization,
            assessment_version=version,
            name="Entrega avanzada E2E",
            course_release=release,
        )
        delivery = activate_delivery(
            actor=owner,
            delivery=delivery,
            expected_version=delivery.lock_version,
        )
        assignment = assign_delivery(
            actor=owner,
            delivery=delivery,
            release_assignment=enrollment.current_release_assignment,
        )
        self.stdout.write(
            "Assessment phase 14 E2E listo: "
            f"assessment={assessment.id}; version={version.id}; "
            f"scoring_revision={correction.id}; delivery={delivery.id}; "
            f"assignment={assignment.id}."
        )
