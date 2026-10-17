"""Static boundaries for dependencies that must stay outside SciRel runtime."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "src" / "scirel"


def _netcdf4_references(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    references: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            if any(name.split(".", 1)[0].lower() == "netcdf4" for name in names):
                references.append((node.lineno, "import"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".", 1)[0].lower() == "netcdf4":
                references.append((node.lineno, "from-import"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.strip()
            if value and value.split(".", 1)[0].lower() == "netcdf4":
                references.append((node.lineno, "dynamic-import-string"))

    return references


def test_runtime_source_does_not_import_netcdf4() -> None:
    violations = {
        str(path.relative_to(ROOT)): _netcdf4_references(path)
        for path in sorted(RUNTIME_ROOT.rglob("*.py"))
        if _netcdf4_references(path)
    }
    assert violations == {}
