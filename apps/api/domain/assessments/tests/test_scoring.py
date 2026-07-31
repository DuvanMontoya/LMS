from decimal import Decimal

from django.test import SimpleTestCase

from ..exceptions import AssessmentInvalid
from ..scoring import (
    basis_points,
    normalize_short_text,
    parse_decimal_text,
    score_question,
)
from .support import question_definition


class DeterministicScoringTests(SimpleTestCase):
    def _score(self, question_type: str, value: object) -> tuple[Decimal, bool]:
        definition = question_definition(question_type)
        result = score_question(
            question_type=question_type,
            grading=definition["grading"],  # type: ignore[arg-type]
            response={
                "schema_version": 1,
                "type": question_type,
                "value": value,
            },
            maximum=Decimal("2.000"),
        )
        return result.score, result.requires_manual

    def test_all_auto_gradable_types_are_all_or_none(self) -> None:
        cases = (
            ("single_choice", "b", "a"),
            ("multiple_choice", ["c", "a"], ["a"]),
            ("true_false", True, False),
            ("numeric", "12,53", "12.56"),
            ("short_text", "  BOGOTÁ ", "Medellín"),
            ("ordering", ["c", "a", "b"], ["a", "b", "c"]),
            ("matching", {"l1": "r1", "l2": "r2"}, {"l1": "r2", "l2": "r1"}),
        )
        for question_type, correct, incorrect in cases:
            with self.subTest(question_type=question_type):
                self.assertEqual(
                    self._score(question_type, correct)[0], Decimal("2.000")
                )
                self.assertEqual(
                    self._score(question_type, incorrect)[0], Decimal("0.000")
                )

    def test_long_text_requires_manual_only_when_answered(self) -> None:
        self.assertEqual(
            self._score("long_text", ""),
            (Decimal("0.000"), False),
        )
        self.assertEqual(
            self._score("long_text", "Argumento sustentado."),
            (Decimal("0.000"), True),
        )

    def test_missing_answers_receive_zero_without_partial_credit(self) -> None:
        for question_type in (
            "single_choice",
            "multiple_choice",
            "true_false",
            "numeric",
            "short_text",
            "long_text",
            "ordering",
            "matching",
        ):
            self.assertEqual(
                self._score(question_type, None),
                (Decimal("0.000"), False),
            )

    def test_numeric_parser_never_accepts_float_or_ambiguous_notation(self) -> None:
        self.assertEqual(parse_decimal_text("1,25"), Decimal("1.25"))
        for value in (1.25, "1,234.5", "1e3", "NaN", "Infinity", "1" * 121):
            with self.subTest(value=value), self.assertRaises(AssessmentInvalid):
                parse_decimal_text(value)

    def test_short_text_normalizes_nfc_whitespace_and_casefold(self) -> None:
        self.assertEqual(
            normalize_short_text("  CAFE\u0301\tCON\nLECHE ", case_sensitive=False),
            "café con leche",
        )

    def test_basis_points_use_decimal_and_floor(self) -> None:
        self.assertEqual(basis_points(score=Decimal("1"), maximum=Decimal("3")), 3333)

    def test_multiple_choice_proportional_credit_and_penalty(self) -> None:
        grading = {
            "correct_option_ids": ["a", "c"],
            "option_ids": ["a", "b", "c", "d"],
        }
        for submitted, expected_credit in (
            (["a", "c"], 10000),
            (["a"], 5000),
            (["a", "b"], 0),
            ([], 0),
        ):
            with self.subTest(submitted=submitted):
                result = score_question(
                    question_type="multiple_choice",
                    scoring_policy="proportional_with_penalty",
                    grading=grading,
                    response={
                        "schema_version": 1,
                        "type": "multiple_choice",
                        "value": submitted,
                    },
                    maximum=Decimal("3.000"),
                )
                self.assertEqual(result.credit_basis_points, expected_credit)
        for invalid in (["a", "a"], ["unknown"]):
            with self.subTest(invalid=invalid), self.assertRaises(AssessmentInvalid):
                score_question(
                    question_type="multiple_choice",
                    scoring_policy="proportional_with_penalty",
                    grading=grading,
                    response={"type": "multiple_choice", "value": invalid},
                    maximum=Decimal("3.000"),
                )

    def test_ordering_partial_credit_policies(self) -> None:
        grading = {"correct_order": ["a", "b", "c", "d"]}
        position = score_question(
            question_type="ordering",
            scoring_policy="position_fraction",
            grading=grading,
            response={"type": "ordering", "value": ["a", "c", "b", "d"]},
            maximum=Decimal("4.000"),
        )
        adjacent = score_question(
            question_type="ordering",
            scoring_policy="adjacent_pair_fraction",
            grading=grading,
            response={"type": "ordering", "value": ["a", "b", "d", "c"]},
            maximum=Decimal("4.000"),
        )
        self.assertEqual(position.credit_basis_points, 5000)
        self.assertEqual(adjacent.credit_basis_points, 3333)

    def test_matching_per_pair_credit(self) -> None:
        result = score_question(
            question_type="matching",
            scoring_policy="per_pair",
            grading={"correct_pairs": {"l1": "r1", "l2": "r2"}},
            response={
                "type": "matching",
                "value": {"l1": "r1", "l2": "r1"},
            },
            maximum=Decimal("2.000"),
        )
        self.assertEqual(result.credit_basis_points, 5000)
        self.assertEqual(result.score, Decimal("1.000"))

    def test_numeric_banded_tolerance_boundaries(self) -> None:
        grading = {
            "correct_value": "10",
            "full_tolerance": "0.1",
            "partial_tolerance": "0.5",
            "partial_credit_basis_points": 4000,
        }
        for value, expected_credit in (
            ("10.1", 10000),
            ("10.5", 4000),
            ("10.5001", 0),
        ):
            with self.subTest(value=value):
                result = score_question(
                    question_type="numeric",
                    scoring_policy="banded_tolerance",
                    grading=grading,
                    response={"type": "numeric", "value": value},
                    maximum=Decimal("1.000"),
                )
                self.assertEqual(result.credit_basis_points, expected_credit)

    def test_score_is_quantized_only_after_credit_is_applied(self) -> None:
        result = score_question(
            question_type="ordering",
            scoring_policy="adjacent_pair_fraction",
            grading={"correct_order": ["a", "b", "c", "d"]},
            response={"type": "ordering", "value": ["a", "b", "d", "c"]},
            maximum=Decimal("1.000"),
        )
        self.assertEqual(result.raw_score, Decimal("0.3333"))
        self.assertEqual(result.score, Decimal("0.333"))
