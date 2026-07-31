from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase


class AssessmentSecurityStaticTests(SimpleTestCase):
    def test_assessment_code_has_no_dynamic_execution_or_unsafe_parsing(self) -> None:
        root = Path(__file__).resolve().parents[1]
        violations: list[str] = []
        forbidden_calls = {
            "__import__",
            "compile",
            "eval",
            "exec",
            "parse_expr",
            "parse_latex",
            "sympify",
        }
        for path in root.rglob("*.py"):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = (
                        [alias.name for alias in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or ""]
                    )
                    if any(
                        name == "pickle" or name.startswith("pickle.") for name in names
                    ):
                        violations.append(f"{path.name}:{node.lineno}:pickle")
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                    violations.append(f"{path.name}:{node.lineno}:{node.func.id}")
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in forbidden_calls | {"load"}
                    and not (
                        node.func.attr == "compile"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "re"
                    )
                    and (
                        node.func.attr != "load"
                        or (
                            isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "yaml"
                        )
                    )
                ):
                    violations.append(f"{path.name}:{node.lineno}:{node.func.attr}")
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "getattr"
                    and (
                        len(node.args) < 2
                        or not isinstance(node.args[1], ast.Constant)
                        or not isinstance(node.args[1].value, str)
                    )
                ):
                    violations.append(f"{path.name}:{node.lineno}:dynamic_getattr")
        self.assertEqual(violations, [])
