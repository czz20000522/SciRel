"""Fail closed when SciRel runtime imports escape the declared dependency layers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib
from typing import Any

from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]
OPTIONAL_CALL = "import_optional_module"
DYNAMIC_CALLS = {"import_module", "__import__"}


@dataclass(frozen=True)
class ImportRecord:
    path: str
    line: int
    module: str
    root: str
    kind: str
    function_depth: int
    extra: str | None = None


class _ImportCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.function_depth = 0
        self.records: list[ImportRecord] = []
        self.unresolved_optional_calls: list[tuple[int, str]] = []

    def _record(self, node: ast.AST, module: str, kind: str, *, extra: str | None = None) -> None:
        if not module or module.startswith("."):
            return
        root = module.split(".", 1)[0]
        self.records.append(
            ImportRecord(
                path=self.path,
                line=getattr(node, "lineno", 0),
                module=module,
                root=root,
                kind=kind,
                function_depth=self.function_depth,
                extra=extra,
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._record(node, alias.name, "import")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0 and node.module:
            self._record(node, node.module, "from-import")

    def visit_Call(self, node: ast.Call) -> None:
        function_name = ""
        if isinstance(node.func, ast.Name):
            function_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            function_name = node.func.attr
        if function_name in DYNAMIC_CALLS | {OPTIONAL_CALL}:
            module = (
                node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else None
            )
            if isinstance(module, str):
                extra = None
                for keyword in node.keywords:
                    if keyword.arg == "extra" and isinstance(keyword.value, ast.Constant):
                        extra = keyword.value.value
                self._record(node, module, "dynamic", extra=extra)
            elif function_name == OPTIONAL_CALL:
                self.unresolved_optional_calls.append((getattr(node, "lineno", 0), self.path))
        self.generic_visit(node)


def _declared_layers(root: Path) -> tuple[set[str], dict[str, set[str]]]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    core = {
        Requirement(value).name.lower().replace("-", "_")
        for value in project.get("dependencies", [])
    }
    optional: dict[str, set[str]] = {}
    for extra, requirements in project.get("optional-dependencies", {}).items():
        optional[extra] = {
            Requirement(value).name.lower().replace("-", "_") for value in requirements
        }
    return core, optional


def validate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    core, optional = _declared_layers(root)
    optional_roots = {name for names in optional.values() for name in names}
    allowed_external = core | optional_roots
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    records: list[ImportRecord] = []
    errors: list[str] = []
    for path in sorted((root / "src/scirel").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        collector = _ImportCollector(relative)
        collector.visit(ast.parse(path.read_text(encoding="utf-8"), filename=relative))
        records.extend(collector.records)
        for line, call_path in collector.unresolved_optional_calls:
            errors.append(f"{call_path}:{line}: optional import must use a literal module name")

    observed_external = set()
    for record in records:
        if record.root in stdlib or record.root == "scirel":
            continue
        observed_external.add(record.root)
        if record.root not in allowed_external:
            errors.append(
                f"{record.path}:{record.line}: undeclared runtime import {record.module!r}"
            )
            continue
        if record.root in optional_roots:
            if record.function_depth == 0:
                errors.append(
                    f"{record.path}:{record.line}: optional import {record.module!r} occurs at module scope"
                )
            if record.kind == "dynamic":
                matching_extras = [name for name, names in optional.items() if record.root in names]
                if record.extra not in matching_extras:
                    errors.append(
                        f"{record.path}:{record.line}: optional import {record.module!r} declares "
                        f"extra {record.extra!r}, expected one of {matching_extras!r}"
                    )

    return {
        "schema": "scirel.runtime-import-closure",
        "status": "PASS" if not errors else "FAIL",
        "core_dependencies": sorted(core),
        "optional_dependencies": {name: sorted(names) for name, names in sorted(optional.items())},
        "observed_external_roots": sorted(observed_external),
        "import_count": len(records),
        "errors": errors,
    }


def main() -> int:
    result = validate()
    import json

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
