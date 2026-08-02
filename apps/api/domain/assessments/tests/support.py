from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from domain.learning.tests.support import LearningFixtureMixin

from ..choices import AuthoringStatus
from ..services import (
    add_assessment_item,
    add_assessment_section,
    create_assessment,
    create_question,
    create_question_bank,
    replace_assessment_objectives,
    transition_assessment_revision,
    transition_question_revision,
)


def prompt_document() -> dict[str, object]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "attrs": {"nodeId": "30000000-0000-4000-8000-000000000001"},
                "content": [{"type": "text", "text": "Responde la pregunta."}],
            }
        ],
    }


def question_definition(question_type: str) -> dict[str, object]:
    public: dict[str, object] = {
        "schema_version": 1,
        "type": question_type,
        "prompt": prompt_document(),
    }
    grading: dict[str, object]
    if question_type in {"single_choice", "multiple_choice", "ordering"}:
        public["options"] = [
            {"id": "a", "label": "Opción A"},
            {"id": "b", "label": "Opción B"},
            {"id": "c", "label": "Opción C"},
        ]
    if question_type == "single_choice":
        grading = {"correct_option_ids": ["b"]}
    elif question_type == "multiple_choice":
        grading = {"correct_option_ids": ["a", "c"]}
    elif question_type == "true_false":
        public["true_label"] = "Verdadero"
        public["false_label"] = "Falso"
        grading = {"correct_boolean": True}
    elif question_type == "numeric":
        public["unit"] = "cm"
        grading = {"correct_value": "12.5", "tolerance": "0.05"}
    elif question_type == "short_text":
        public["response_placeholder"] = "Respuesta breve"
        grading = {
            "accepted_answers": ["Bogotá", "Santa Fe de Bogotá"],
            "case_sensitive": False,
        }
    elif question_type == "long_text":
        public["response_placeholder"] = "Sustenta tu respuesta"
        grading = {"manual_required": True, "rubric": "Claridad y evidencia."}
    elif question_type == "ordering":
        grading = {"correct_order": ["c", "a", "b"]}
    elif question_type == "matching":
        public["left"] = [
            {"id": "l1", "label": "Dos"},
            {"id": "l2", "label": "Tres"},
        ]
        public["right"] = [
            {"id": "r1", "label": "2"},
            {"id": "r2", "label": "3"},
        ]
        grading = {"correct_pairs": {"l1": "r1", "l2": "r2"}}
    elif question_type == "mathematical_expression":
        public["allowed_symbols"] = ["x"]
        public["allowed_functions"] = []
        public["response_guidance"] = "Escribe una expresión equivalente."
        public["maximum_latex_length"] = 4096
        grading = {
            "expected_mathjson": ["Add", "x", 1],
            "equivalence_strategy": "structural",
            "symbol_assumptions": {"x": ["real"]},
            "allowed_symbols": ["x"],
            "allowed_functions": [],
        }
    else:
        raise AssertionError(f"Unsupported type: {question_type}")
    return {
        "schema_version": 1,
        "type": question_type,
        "public": public,
        "grading": grading,
        "feedback": {
            "general": "Revisa el concepto evaluado.",
            "correct": "Correcto.",
            "incorrect": "Inténtalo de nuevo.",
        },
    }


class AssessmentFixtureMixin(LearningFixtureMixin):
    def assessment_context(self, *, with_learning: bool = False):
        if with_learning:
            (
                owner,
                learner,
                organization,
                membership,
                revision,
                _module,
                _unit,
                _publication,
                release,
                enrollment,
            ) = self.learning_context()
            objective = revision.objective_alignments.first().learning_objective
            course_revision = revision
        else:
            owner, organization, _, objective, _, course_revision = (
                self.course_revision()
            )
            learner = membership = release = enrollment = None

        bank = create_question_bank(
            actor=owner,
            organization=organization,
            name="Banco de álgebra",
            slug="algebra",
        )
        question, question_revision = create_question(
            actor=owner,
            bank=bank,
            code="ALG-Q-001",
            question_type="single_choice",
            definition=question_definition("single_choice"),
        )
        question_revision, _ = transition_question_revision(
            actor=owner,
            revision=question_revision,
            expected_version=question_revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        question_revision, question_version = transition_question_revision(
            actor=owner,
            revision=question_revision,
            expected_version=question_revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        assert question_version is not None

        assessment, assessment_revision = create_assessment(
            actor=owner,
            organization=organization,
            slug="diagnostico-algebra",
            title="Diagnóstico de álgebra",
            description="Evaluación inicial.",
            time_limit_minutes=30,
            attempt_limit=2,
            pass_basis_points=6000,
        )
        assessment_revision = replace_assessment_objectives(
            actor=owner,
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            objectives=[objective],
        )
        assessment_revision, section = add_assessment_section(
            actor=owner,
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            title="Conceptos fundamentales",
        )
        assessment_revision, item = add_assessment_item(
            actor=owner,
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            section=section,
            question_version=question_version,
            points=Decimal("2.000"),
            required=True,
            objectives=[objective],
        )
        assessment_revision, _ = transition_assessment_revision(
            actor=owner,
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        assessment_revision, assessment_version = transition_assessment_revision(
            actor=owner,
            revision=assessment_revision,
            expected_version=assessment_revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        assert assessment_version is not None
        return {
            "owner": owner,
            "learner": learner,
            "organization": organization,
            "course_revision": course_revision,
            "membership": membership,
            "release": release,
            "enrollment": enrollment,
            "bank": bank,
            "question": question,
            "question_revision": question_revision,
            "question_version": question_version,
            "assessment": assessment,
            "assessment_revision": assessment_revision,
            "assessment_version": assessment_version,
            "section": section,
            "item": item,
            "objective": objective,
        }


def cloned_definition(question_type: str) -> dict[str, object]:
    return deepcopy(question_definition(question_type))
