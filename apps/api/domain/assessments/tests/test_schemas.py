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
