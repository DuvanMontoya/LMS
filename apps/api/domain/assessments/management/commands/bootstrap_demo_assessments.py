# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from domain.assessments.choices import (
    AttemptAggregation,
    AuthoringStatus,
    DeliveryStatus,
    GradebookStatus,
)
from domain.assessments.gradebooks import (
    activate_gradebook,
    add_gradebook_column,
    create_gradebook,
)
from domain.assessments.grading import create_scoring_correction
from domain.assessments.models import (
    Assessment,
    AssessmentDelivery,
    CourseGradebook,
    DeliveryAssignment,
    Question,
    QuestionBank,
)
from domain.assessments.services import (
    activate_delivery,
    add_assessment_item,
    add_assessment_section,
    assign_delivery,
    create_assessment,
    create_assessment_pool,
    create_assessment_revision_from_version,
    create_delivery,
    create_question,
    create_question_bank,
    replace_assessment_objectives,
    transition_assessment_revision,
    transition_question_revision,
    update_question_bank,
)
from domain.catalog.models import LearningObjective
from domain.learning.models import CourseEnrollment
from domain.organizations.models import Organization

DEMO_ORGANIZATION = "organizacion-demo"
DEMO_ASSESSMENT = "diagnostico-calculo"
DEMO_BANK = "fundamentos-calculo"


def _prompt(text: str, index: int) -> dict[str, object]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {
                    "nodeId": f"30000000-0000-4000-8000-{index:012d}",
                },
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def demo_question_definition(question_type: str, index: int) -> dict[str, object]:
    public: dict[str, object] = {
        "schema_version": 1,
        "type": question_type,
        "prompt": _prompt(
            f"Pregunta demo {index}: responde según el concepto presentado.", index
        ),
    }
    if question_type in {
        "single_choice",
        "multiple_choice",
        "ordering",
    }:
        public["options"] = [
            {"id": "a", "label": "Primera opción"},
            {"id": "b", "label": "Segunda opción"},
            {"id": "c", "label": "Tercera opción"},
        ]
    if question_type == "single_choice":
        grading = {"correct_option_ids": ["b"]}
    elif question_type == "multiple_choice":
        grading = {"correct_option_ids": ["a", "c"]}
    elif question_type == "true_false":
        public.update({"true_label": "Verdadero", "false_label": "Falso"})
        grading = {"correct_boolean": True}
    elif question_type == "numeric":
        public["unit"] = "unidades"
        grading = {"correct_value": "12.5", "tolerance": "0.05"}
    elif question_type == "short_text":
        public["response_placeholder"] = "Respuesta breve"
        grading = {"accepted_answers": ["derivada"], "case_sensitive": False}
    elif question_type == "long_text":
        public["response_placeholder"] = "Explica tu razonamiento"
        grading = {
            "manual_required": True,
            "rubric": "Claridad conceptual y justificación.",
        }
    elif question_type == "ordering":
        grading = {"correct_order": ["c", "a", "b"]}
    elif question_type == "matching":
        public["left"] = [
            {"id": "l1", "label": "Derivada"},
            {"id": "l2", "label": "Integral"},
        ]
        public["right"] = [
            {"id": "r1", "label": "Tasa de cambio"},
            {"id": "r2", "label": "Acumulación"},
        ]
        grading = {"correct_pairs": {"l1": "r1", "l2": "r2"}}
    elif question_type == "mathematical_expression":
        public.update(
            {
                "allowed_symbols": ["x"],
                "allowed_functions": [],
                "response_guidance": "Escribe una expresión equivalente en x.",
                "maximum_latex_length": 4096,
            }
        )
        grading = {
            "expected_mathjson": ["Add", "x", 1],
            "equivalence_strategy": "symbolic_common_domain",
            "symbol_assumptions": {"x": ["real"]},
            "allowed_symbols": ["x"],
            "allowed_functions": [],
        }
    else:
        raise AssertionError(f"Tipo no soportado: {question_type}")
    return {
        "schema_version": 1,
        "type": question_type,
        "public": public,
        "grading": grading,
        "feedback": {
            "general": "Consulta el material del curso.",
            "correct": "Respuesta correcta.",
            "incorrect": "Revisa el concepto.",
        },
    }


class Command(BaseCommand):
    help = (
        "Crea nueve tipos, pool, scoring v2, gradebook y entrega demo "
        "sólo en desarrollo."
    )

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("Assessments demo sólo se permite con DEBUG=True.")
        organization = Organization.objects.filter(slug=DEMO_ORGANIZATION).first()
        owner = get_user_model().objects.filter(email="owner@demo.local").first()
        if organization is None or owner is None:
            raise CommandError("Ejecuta primero el demo de organizaciones.")
        objective = (
            LearningObjective.objects.filter(
                subject__discipline__area__organization=organization,
                status="active",
            )
            .order_by("code")
            .first()
        )
        enrollment = (
            CourseEnrollment.objects.filter(
                membership__organization=organization,
                membership__user__email="learner@demo.local",
                status="active",
            )
            .select_related("current_release_assignment__release")
            .first()
        )
        if (
            objective is None
            or enrollment is None
            or enrollment.current_release_assignment is None
        ):
            raise CommandError(
                "Ejecuta primero los demos de catálogo, publicación y learning."
            )

        bank = QuestionBank.objects.filter(
            organization=organization, slug=DEMO_BANK
        ).first()
        if bank is None:
            bank = create_question_bank(
                actor=owner,
                organization=organization,
                name="Fundamentos de cálculo",
                slug=DEMO_BANK,
                description="Banco demo con nueve tipos y candidatos de pool.",
            )
        elif bank.description != "Banco demo con nueve tipos y candidatos de pool.":
            bank = update_question_bank(
                actor=owner,
                bank=bank,
                expected_version=bank.lock_version,
                name=bank.name,
                description="Banco demo con nueve tipos y candidatos de pool.",
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
            "mathematical_expression",
        )
        for index, question_type in enumerate(question_types, start=1):
            code = f"CAL-DEMO-{index:03d}"
            question = Question.objects.filter(bank=bank, code=code).first()
            if question is None:
                question, revision = create_question(
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
            else:
                version = question.versions.order_by("-number").first()
            if version is None:
                raise CommandError(f"La pregunta demo {code} no tiene versión.")
            versions.append(version)

        pool_versions = []
        for index in range(1, 11):
            code = f"CAL-POOL-{index:03d}"
            question = Question.objects.filter(bank=bank, code=code).first()
            if question is None:
                question, revision = create_question(
                    actor=owner,
                    bank=bank,
                    code=code,
                    question_type="single_choice",
                    definition=demo_question_definition("single_choice", 100 + index),
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
            else:
                version = question.versions.order_by("-number").first()
            if version is None:
                raise CommandError(f"La pregunta demo {code} no tiene versión.")
            pool_versions.append(version)

        assessment = Assessment.objects.filter(
            organization=organization, slug=DEMO_ASSESSMENT
        ).first()
        if assessment is None:
            assessment, revision = create_assessment(
                actor=owner,
                organization=organization,
                slug=DEMO_ASSESSMENT,
                title="Diagnóstico de fundamentos de cálculo",
                description=(
                    "Evaluación demo con nueve tipos, crédito parcial, "
                    "expresión matemática y pool."
                ),
                instructions="Guarda cada respuesta y confirma el envío final.",
                time_limit_minutes=45,
                attempt_limit=2,
                pass_basis_points=6000,
                feedback_mode="full_after_grading",
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
                title="Nueve tipos de pregunta",
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
            revision, _ = create_assessment_pool(
                actor=owner,
                revision=revision,
                expected_version=revision.lock_version,
                title="Variantes aleatorias de fundamentos",
                instructions="El sistema selecciona tres variantes sin reemplazo.",
                selection_count=3,
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
            _, assessment_version = transition_assessment_revision(
                actor=owner,
                revision=revision,
                expected_version=revision.lock_version,
                to_status=AuthoringStatus.APPROVED,
            )
        else:
            assessment_version = assessment.versions.order_by("-number").first()
        if assessment_version is None:
            raise CommandError("La evaluación demo no tiene versión aprobada.")
        snapshot_types = {
            item["question"]["type"]
            for section in assessment_version.public_snapshot["sections"]
            for item in section["items"]
        }
        if (
            "mathematical_expression" not in snapshot_types
            or not assessment_version.public_snapshot.get("pools")
        ):
            revision = create_assessment_revision_from_version(
                actor=owner,
                version=assessment_version,
            )
            section = revision.sections.order_by("position").first()
            if section is None:
                raise CommandError("La evaluación demo no tiene sección base.")
            fixed_version_ids = set(
                section.items.values_list("question_version_id", flat=True)
            )
            math_version = versions[-1]
            if math_version.id not in fixed_version_ids:
                revision, _ = add_assessment_item(
                    actor=owner,
                    revision=revision,
                    expected_version=revision.lock_version,
                    section=section,
                    question_version=math_version,
                    points=Decimal("1.000"),
                    required=True,
                    objectives=[objective],
                )
            if not revision.item_pools.exists():
                revision, _ = create_assessment_pool(
                    actor=owner,
                    revision=revision,
                    expected_version=revision.lock_version,
                    title="Variantes aleatorias de fundamentos",
                    instructions=(
                        "El sistema selecciona tres variantes sin reemplazo."
                    ),
                    selection_count=3,
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
            _, assessment_version = transition_assessment_revision(
                actor=owner,
                revision=revision,
                expected_version=revision.lock_version,
                to_status=AuthoringStatus.APPROVED,
            )
            if assessment_version is None:
                raise CommandError("No se pudo aprobar la versión avanzada.")

        policy = assessment_version.grading_policy
        current_scoring = policy.current_revision
        if current_scoring is None:
            raise CommandError("La evaluación demo no tiene scoring policy.")
        if current_scoring.number == 1:
            overrides: dict[str, dict[str, object]] = {}
            for item in current_scoring.grading_snapshot["items"]:
                question_type = item["question_type"]
                grading_payload = dict(item["grading_payload"])
                if question_type == "multiple_choice":
                    overrides[item["source_id"]] = {
                        "scoring_policy": "proportional_with_penalty",
                        "grading_payload": grading_payload,
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
            if overrides:
                current_scoring = create_scoring_correction(
                    actor=owner,
                    assessment_version=assessment_version,
                    expected_policy_version=policy.lock_version,
                    reason=(
                        "Configura crédito parcial determinista para el demo avanzado."
                    ),
                    item_overrides=overrides,
                )

        delivery = AssessmentDelivery.objects.filter(
            organization=organization, name="Diagnóstico avanzado demo activo"
        ).first()
        if delivery is None:
            delivery = create_delivery(
                actor=owner,
                organization=organization,
                assessment_version=assessment_version,
                name="Diagnóstico avanzado demo activo",
                course_release=enrollment.current_release_assignment.release,
            )
        if delivery.status == DeliveryStatus.DRAFT:
            delivery = activate_delivery(
                actor=owner,
                delivery=delivery,
                expected_version=delivery.lock_version,
            )
        assignment = DeliveryAssignment.objects.filter(
            delivery=delivery,
            release_assignment=enrollment.current_release_assignment,
        ).first()
        if assignment is None:
            assignment = assign_delivery(
                actor=owner,
                delivery=delivery,
                release_assignment=enrollment.current_release_assignment,
            )
        gradebook = CourseGradebook.objects.filter(
            course_release=enrollment.current_release_assignment.release
        ).first()
        if gradebook is None:
            gradebook = create_gradebook(
                actor=owner,
                organization=organization,
                course_release=enrollment.current_release_assignment.release,
            )
        if gradebook.status == GradebookStatus.DRAFT:
            column = gradebook.columns.filter(delivery=delivery).first()
            if column is None and not gradebook.columns.exists():
                gradebook, _ = add_gradebook_column(
                    actor=owner,
                    gradebook=gradebook,
                    expected_version=gradebook.lock_version,
                    delivery=delivery,
                    title="Diagnóstico avanzado",
                    weight_basis_points=10_000,
                    required=True,
                    attempt_aggregation=AttemptAggregation.HIGHEST,
                )
            if (
                gradebook.columns.filter(status="active").count() == 1
                and gradebook.columns.filter(status="active")
                .first()
                .weight_basis_points
                == 10_000
            ):
                gradebook = activate_gradebook(
                    actor=owner,
                    gradebook=gradebook,
                    expected_version=gradebook.lock_version,
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Assessments demo conservado: "
                f"bank={bank.id}; assessment={assessment.id}; "
                f"delivery={delivery.id}; assignment={assignment.id}; "
                f"gradebook={gradebook.id}; scoring_revision={current_scoring.id}."
            )
        )
