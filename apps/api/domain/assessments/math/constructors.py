# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOperatorIssue=false, reportReturnType=false
from __future__ import annotations

from collections.abc import Collection, Mapping
from decimal import Decimal

from sympy import Abs as SympyAbs
from sympy import (
    Add,
    E,
    Integer,
    Mul,
    Pow,
    Rational,
    Symbol,
    cos,
    exp,
    log,
    pi,
    sin,
    tan,
)
from sympy.core.expr import Expr

from ..exceptions import AssessmentInvalid
from .ast import DECIMAL_PATTERN, MathJson, validate_mathjson


def _decimal_rational(value: str) -> Rational:
    decimal = Decimal(value)
    sign, digits, exponent = decimal.as_tuple()
    numerator = int("".join(str(digit) for digit in digits) or "0")
    if sign:
        numerator = -numerator
    if exponent >= 0:
        return Rational(numerator * (10**exponent), 1)
    return Rational(numerator, 10 ** (-exponent))


def _symbols(
    allowed_symbols: Collection[str],
    assumptions: Mapping[str, Collection[str]],
) -> dict[str, Symbol]:
    result: dict[str, Symbol] = {}
    for name in allowed_symbols:
        declared = set(assumptions.get(name, ()))
        unknown = declared - {"real", "positive", "nonnegative", "integer"}
        if unknown:
            raise AssessmentInvalid("Una assumption matemática no está permitida.")
        kwargs: dict[str, bool] = {}
        if "positive" in declared:
            kwargs.update(real=True, positive=True)
        elif "nonnegative" in declared:
            kwargs.update(real=True, nonnegative=True)
        elif "real" in declared:
            kwargs["real"] = True
        if "integer" in declared:
            kwargs["integer"] = True
        result[name] = Symbol(name, **kwargs)
    if set(assumptions) - set(allowed_symbols):
        raise AssessmentInvalid("Las assumptions incluyen un símbolo no autorizado.")
    return result


def build_sympy_expression(
    value: object,
    *,
    allowed_symbols: Collection[str],
    allowed_functions: Collection[str],
    assumptions: Mapping[str, Collection[str]],
) -> Expr:
    validated = validate_mathjson(
        value,
        allowed_symbols=allowed_symbols,
        allowed_functions=allowed_functions,
    )
    symbols = _symbols(allowed_symbols, assumptions)

    def build(node: MathJson) -> Expr:
        if isinstance(node, int):
            return Integer(node)
        if isinstance(node, str):
            if DECIMAL_PATTERN.fullmatch(node):
                return _decimal_rational(node)
            if node == "Pi":
                return pi
            if node == "ExponentialE":
                return E
            if node in symbols:
                return symbols[node]
            raise AssessmentInvalid("MathJSON usa un símbolo no autorizado.")

        operator = node[0]
        if operator == "Rational":
            return Rational(node[1], node[2])
        arguments = [build(argument) for argument in node[1:]]
        if operator == "Add":
            return Add(*arguments)
        if operator == "Subtract":
            return Add(arguments[0], Mul(Integer(-1), arguments[1]))
        if operator == "Negate":
            return Mul(Integer(-1), arguments[0])
        if operator == "Multiply":
            return Mul(*arguments)
        if operator == "Divide":
            return Mul(arguments[0], Pow(arguments[1], Integer(-1)))
        if operator == "Power":
            return Pow(arguments[0], arguments[1])
        if operator == "Sqrt":
            return Pow(arguments[0], Rational(1, 2))
        if operator == "Root":
            return Pow(arguments[0], Pow(arguments[1], Integer(-1)))
        if operator == "Abs":
            return SympyAbs(arguments[0])
        if operator == "Sin":
            return sin(arguments[0])
        if operator == "Cos":
            return cos(arguments[0])
        if operator == "Tan":
            return tan(arguments[0])
        if operator == "Exp":
            return exp(arguments[0])
        if operator in {"Ln", "Log"}:
            return log(*arguments)
        raise AssessmentInvalid("MathJSON usa un operador no autorizado.")

    return build(validated)
