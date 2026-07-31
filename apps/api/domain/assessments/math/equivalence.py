# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportAttributeAccessIssue=false, reportCallIssue=false, reportArgumentType=false, reportReturnType=false
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Literal

from sympy import Rational, cancel, simplify, together
from sympy.core.expr import Expr
from sympy.core.function import count_ops

from ..exceptions import AssessmentInvalid
from .constructors import build_sympy_expression
from .limits import (
    COUNTEREXAMPLE_POINTS,
    MAX_COUNTEREXAMPLE_EVALUATIONS,
    MAX_SYMBOLIC_OPERATIONS,
)


@dataclass(frozen=True)
class MathEquivalenceOutcome:
    status: Literal["equivalent", "not_equivalent", "inconclusive"]
    counterexample_found: bool


def _bounded(expression: Expr) -> None:
    if int(count_ops(expression, visual=False)) > MAX_SYMBOLIC_OPERATIONS:
        raise AssessmentInvalid("La expresión supera el límite de operaciones.")


def _sample_value(value: int | str) -> Rational:
    if isinstance(value, int):
        return Rational(value, 1)
    numerator, denominator = value.split("/", 1)
    return Rational(int(numerator), int(denominator))


def _counterexample(lhs: Expr, rhs: Expr) -> bool:
    symbols = sorted(
        lhs.free_symbols | rhs.free_symbols, key=lambda symbol: symbol.name
    )
    if not symbols:
        return bool((lhs - rhs).evalf(50) != 0)
    evaluations = 0
    points = tuple(_sample_value(value) for value in COUNTEREXAMPLE_POINTS)
    for values in product(points, repeat=len(symbols)):
        substitutions = dict(zip(symbols, values, strict=True))
        try:
            left = lhs.subs(substitutions)
            right = rhs.subs(substitutions)
            if left.is_finite is False or right.is_finite is False:
                continue
            difference = (left - right).evalf(50)
            if difference.is_finite is False:
                continue
            evaluations += 1
            if difference != 0:
                return True
        except (ArithmeticError, ValueError, TypeError):
            continue
        if evaluations >= MAX_COUNTEREXAMPLE_EVALUATIONS:
            break
    return False


def evaluate_equivalence(
    *,
    expected_mathjson: object,
    submitted_mathjson: object,
    allowed_symbols: list[str],
    allowed_functions: list[str],
    symbol_assumptions: dict[str, list[str]],
) -> MathEquivalenceOutcome:
    expected = build_sympy_expression(
        expected_mathjson,
        allowed_symbols=allowed_symbols,
        allowed_functions=allowed_functions,
        assumptions=symbol_assumptions,
    )
    submitted = build_sympy_expression(
        submitted_mathjson,
        allowed_symbols=allowed_symbols,
        allowed_functions=allowed_functions,
        assumptions=symbol_assumptions,
    )
    _bounded(expected)
    _bounded(submitted)
    if expected == submitted:
        return MathEquivalenceOutcome("equivalent", False)
    difference = expected - submitted
    for candidate in (cancel(together(difference)), simplify(difference)):
        _bounded(candidate)
        if candidate == 0 or candidate.is_zero is True:
            return MathEquivalenceOutcome("equivalent", False)
        if not candidate.free_symbols and candidate.is_zero is False:
            return MathEquivalenceOutcome("not_equivalent", False)
    found = _counterexample(expected, submitted)
    return MathEquivalenceOutcome(
        "not_equivalent" if found else "inconclusive",
        found,
    )
