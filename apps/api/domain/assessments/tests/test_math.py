from django.test import SimpleTestCase

from ..exceptions import AssessmentInvalid
from ..math import canonical_mathjson, evaluate_equivalence, validate_mathjson
from ..math.constructors import build_sympy_expression


class SafeMathJsonTests(SimpleTestCase):
    def test_structural_canonicalization_is_deterministic(self) -> None:
        left = validate_mathjson(
            ["Divide", ["Subtract", ["Power", "x", 2], 1], ["Subtract", "x", 1]],
            allowed_symbols=["x"],
            allowed_functions=[],
        )
        right = validate_mathjson(
            ["Divide", ["Subtract", ["Power", "x", 2], 1], ["Subtract", "x", 1]],
            allowed_symbols=["x"],
            allowed_functions=[],
        )
        self.assertEqual(canonical_mathjson(left), canonical_mathjson(right))

    def test_explicit_constructor_supports_assumptions_and_common_domain(self) -> None:
        expression = build_sympy_expression(
            ["Add", "x", 1],
            allowed_symbols=["x"],
            allowed_functions=[],
            assumptions={"x": ["real"]},
        )
        self.assertEqual({symbol.name for symbol in expression.free_symbols}, {"x"})
        outcome = evaluate_equivalence(
            expected_mathjson=1,
            submitted_mathjson=["Divide", "x", "x"],
            allowed_symbols=["x"],
            allowed_functions=[],
            symbol_assumptions={"x": ["real"]},
        )
        self.assertEqual(outcome.status, "equivalent")

    def test_symbolic_equivalence_and_counterexample_are_exact(self) -> None:
        trigonometric = evaluate_equivalence(
            expected_mathjson=1,
            submitted_mathjson=[
                "Add",
                ["Power", ["Sin", "x"], 2],
                ["Power", ["Cos", "x"], 2],
            ],
            allowed_symbols=["x"],
            allowed_functions=["Sin", "Cos"],
            symbol_assumptions={"x": ["real"]},
        )
        different = evaluate_equivalence(
            expected_mathjson=["Add", "x", 1],
            submitted_mathjson=["Add", "x", 2],
            allowed_symbols=["x"],
            allowed_functions=[],
            symbol_assumptions={"x": ["real"]},
        )
        self.assertEqual(trigonometric.status, "equivalent")
        self.assertEqual(different.status, "not_equivalent")

    def test_sampling_only_refutes_and_can_remain_inconclusive(self) -> None:
        roots = [
            -5,
            -3,
            -2,
            -1,
            ["Rational", -1, 2],
            ["Rational", 1, 2],
            1,
            2,
            3,
            5,
        ]
        polynomial = [
            "Multiply",
            *[["Subtract", "x", root] for root in roots],
        ]
        outcome = evaluate_equivalence(
            expected_mathjson=0,
            submitted_mathjson=polynomial,
            allowed_symbols=["x"],
            allowed_functions=[],
            symbol_assumptions={"x": ["real"]},
        )
        self.assertEqual(outcome.status, "inconclusive")
        self.assertFalse(outcome.counterexample_found)

    def test_dangerous_or_oversized_ast_is_rejected(self) -> None:
        invalid_values = (
            ["Assign", "x", 1],
            ["Power", "x", 21],
            ["Sin", "x"],
            {"fn": "Add", "args": ["x", 1]},
            ["Add", *(1 for _ in range(51))],
        )
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(AssessmentInvalid):
                validate_mathjson(
                    value,
                    allowed_symbols=["x"],
                    allowed_functions=[],
                )
