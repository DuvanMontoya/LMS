from copy import deepcopy

from django.test import SimpleTestCase

from ..exceptions import AssessmentInvalid
from ..schemas import (
    validate_question_definition,
    validate_response,
    validate_schema_contracts,
)
from .support import question_definition

QUESTION_TYPES = (
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


class AssessmentSchemaTests(SimpleTestCase):
    def test_all_four_draft_2020_12_contracts_compile(self) -> None:
        validate_schema_contracts()

    def test_exactly_nine_question_types_validate(self) -> None:
        for question_type in QUESTION_TYPES:
            with self.subTest(question_type=question_type):
                validated = validate_question_definition(
                    question_definition(question_type)
                )
                self.assertEqual(validated["type"], question_type)
                self.assertNotIn("grading", validated["public"])

    def test_public_type_must_match_definition_type(self) -> None:
        definition = question_definition("single_choice")
        definition["public"]["type"] = "multiple_choice"  # type: ignore[index]
        with self.assertRaises(AssessmentInvalid):
            validate_question_definition(definition)

    def test_choice_key_cannot_reference_a_hidden_option(self) -> None:
        definition = question_definition("single_choice")
        definition["grading"]["correct_option_ids"] = ["secret"]  # type: ignore[index]
        with self.assertRaises(AssessmentInvalid):
            validate_question_definition(definition)

    def test_choice_image_requires_an_informative_text_alternative(self) -> None:
        definition = question_definition("single_choice")
        definition["public"]["options"][0]["media"] = {  # type: ignore[index]
            "asset_version_id": "50000000-0000-4000-8000-000000000001",
            "kind": "image",
            "alt_text": "Gráfica de una función creciente.",
            "long_description": "La curva cruza el origen y crece para x positivo.",
        }
        validate_question_definition(definition)
        definition["public"]["options"][0]["media"]["alt_text"] = ""  # type: ignore[index]
        with self.assertRaises(AssessmentInvalid):
            validate_question_definition(definition)

    def test_question_math_accepts_latex_but_rejects_unsafe_capabilities(self) -> None:
        definition = question_definition("single_choice")
        definition["public"]["prompt"]["content"].append(  # type: ignore[index]
            {
                "type": "displayMath",
                "attrs": {
                    "nodeId": "50000000-0000-4000-8000-000000000004",
                    "latex": r"\int_0^1 x^2\,dx",
                },
            }
        )
        definition["public"]["options"][0]["math_latex"] = r"x^2+2x+1"  # type: ignore[index]
        validate_question_definition(definition)
        definition["public"]["options"][0]["math_latex"] = r"\require{texhtml}"  # type: ignore[index]
        with self.assertRaises(AssessmentInvalid):
            validate_question_definition(definition)

    def test_authoring_blueprint_and_worked_solution_are_private_validated_content(
        self,
    ) -> None:
        definition = question_definition("single_choice")
        definition["authoring"] = {
            "framework": "icfes",
            "difficulty": "advanced",
            "cognitive_process": "analyze",
            "estimated_minutes": 6,
            "tags": ["algebra", "modelacion"],
            "source_note": "Adaptación editorial interna.",
            "choice_rationales": {
                "a": "Respuesta válida por proporcionalidad.",
                "b": "Confunde razón con diferencia absoluta.",
            },
        }
        definition["worked_solution"] = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"nodeId": "50000000-0000-4000-8000-000000000005"},
                    "content": [{"type": "text", "text": "Se despeja la razón."}],
                },
                {
                    "type": "displayMath",
                    "attrs": {
                        "nodeId": "50000000-0000-4000-8000-000000000006",
                        "latex": r"x=\frac{30}{120}",
                    },
                },
            ],
        }
        validated = validate_question_definition(definition)
        self.assertEqual(validated["authoring"]["framework"], "icfes")
        self.assertIn("worked_solution", validated)

    def test_choice_rationale_cannot_reference_a_nonexistent_option(self) -> None:
        definition = question_definition("single_choice")
        definition["authoring"] = {
            "choice_rationales": {"hidden": "No existe en el payload público."}
        }
        with self.assertRaises(AssessmentInvalid):
            validate_question_definition(definition)

    def test_worked_solution_rejects_unsafe_math_capabilities(self) -> None:
        definition = question_definition("single_choice")
        definition["worked_solution"] = {
            "type": "doc",
            "content": [
                {
                    "type": "displayMath",
                    "attrs": {
                        "nodeId": "50000000-0000-4000-8000-000000000007",
                        "latex": r"\require{texhtml}",
                    },
                }
            ],
        }
        with self.assertRaises(AssessmentInvalid):
            validate_question_definition(definition)

    def test_normalized_short_answer_collisions_are_rejected(self) -> None:
        definition = question_definition("short_text")
        definition["grading"]["accepted_answers"] = ["Bogotá", " BOGOTÁ "]  # type: ignore[index]
        with self.assertRaises(AssessmentInvalid):
            validate_question_definition(definition)

    def test_response_type_is_bound_to_attempt_item(self) -> None:
        response = {
            "schema_version": 1,
            "type": "single_choice",
            "value": "a",
        }
        validate_response(response, expected_type="single_choice")
        with self.assertRaises(AssessmentInvalid):
            validate_response(deepcopy(response), expected_type="multiple_choice")
