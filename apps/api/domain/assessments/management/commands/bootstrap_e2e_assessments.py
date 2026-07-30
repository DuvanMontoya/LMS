# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.assessments.choices import AuthoringStatus
from domain.assessments.services import (
    activate_delivery,
    add_assessment_item,
    add_assessment_section,
    assign_delivery,
    create_assessment,
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
from domain.learning.services import enroll_member
from domain.organizations.models import Membership, Organization
from domain.publishing.models import CoursePublication

from .bootstrap_demo_assessments import demo_question_definition


class Command(BaseCommand):
    help = "Crea la evaluación efímera requerida por el E2E aislado."

    def handle(self, *args: object, **options: object) -> None:
        if settings.SETTINGS_MODULE != "config.settings.e2e":
            raise CommandError("Este comando sólo puede ejecutarse con settings E2E.")
        with transaction.atomic():
            self._bootstrap()

    def _bootstrap(self) -> None:
        organization = Organization.objects.get(slug="organizacion-a")
        owner = User.objects.get(email="owner@organizations.e2e.test")
        learner = User.objects.get(email="learner@organizations.e2e.test")
        membership = Membership.objects.get(organization=organization, user=learner)
        course = Course.objects.get(
            organization=organization, slug="publicacion-inmutable-e2e"
        )
        publication = CoursePublication.objects.select_related("current_release").get(
            course=course
        )
        release = publication.current_release
        if release is None:
            raise CommandError("Falta el release E2E.")
        enrollment = CourseEnrollment.objects.filter(
            membership=membership, course=course
        ).first()
        if enrollment is None:
            enrollment = enroll_member(
                actor=owner,
                organization=organization,
                course=course,
                membership=membership,
                release=release,
            )
        objective = (
            LearningObjective.objects.filter(
                subject__discipline__area__organization=organization,
                status="active",
            )
            .order_by("code")
            .first()
        )
        if objective is None:
            raise CommandError("Falta un objetivo E2E.")
        bank = create_question_bank(
            actor=owner,
            organization=organization,
            name="Banco E2E de assessments",
            slug="banco-assessments-e2e",
        )
        versions = []
        question_types = (
            "single_choice",
            "multiple_choice",
            "true_false",
            "numeric",
            "short_text",
            "long_text",
            "ordering",
            "matching",
        )
        for index, question_type in enumerate(question_types, start=1):
            _, revision = create_question(
                actor=owner,
                bank=bank,
                code=f"ASSESS-E2E-{index:03d}",
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
            versions.append(version)
        _, revision = create_assessment(
            actor=owner,
            organization=organization,
            slug="diagnostico-assessments-e2e",
            title="Diagnóstico integral E2E",
            description="Cubre los ocho tipos y calificación manual.",
            instructions="Guarda cada respuesta.",
            time_limit_minutes=30,
            attempt_limit=2,
            pass_basis_points=6000,
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
            title="Sección integral",
        )
        for version in versions:
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
        delivery = create_delivery(
            actor=owner,
            organization=organization,
            assessment_version=version,
            name="Entrega E2E activa",
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
            f"Assessment E2E listo: bank={bank.id}; assignment={assignment.id}."
        )
