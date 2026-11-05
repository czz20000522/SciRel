"""Static boundaries for dependencies that must stay outside SciRel runtime."""

from __future__ import annotations

import ast
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "src" / "scirel"
sys.path.insert(0, str(ROOT / "scripts"))

from validate_runtime_imports import validate  # noqa: E402


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


def test_declared_runtime_import_closure_is_complete() -> None:
    result = validate(ROOT)

    assert result["status"] == "PASS"
    assert result["core_dependencies"] == ["mpmath", "numpy", "scipy"]
    assert result["optional_dependencies"] == {}
    assert result["observed_external_roots"] == ["mpmath", "numpy", "scipy"]
    assert result["errors"] == []


def _copy_runtime_tree(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    shutil.copytree(ROOT / "src", root / "src")
    shutil.copy2(ROOT / "pyproject.toml", root / "pyproject.toml")
    return root


def test_runtime_import_guard_rejects_undeclared_dependency(tmp_path: Path) -> None:
    root = _copy_runtime_tree(tmp_path)
    target = root / "src/scirel/geometry/sampling.py"
    target.write_text(
        "import unknown_scirel_dependency\n" + target.read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = validate(root)

    assert result["status"] == "FAIL"
    assert any("unknown_scirel_dependency" in error for error in result["errors"])
