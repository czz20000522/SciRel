"""Select SciRel tests from changed files and exact asset dependencies."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "provenance" / "admitted-assets.json"
SCHEMA = "scirel.affected-tests.v1"

DIRECT_TEST_OVERRIDES = {
    "scirel.inference.anisotropic_trial_evaluation.evaluate_anisotropic_trial": (
        "tests/test_incremental_admissions.py"
    ),
}

FULL_SUITE_PATHS = {
    "provenance/admitted-assets.json",
    "pyproject.toml",
}

ENGINEERING_TESTS = {
    "examples/user_acceptance.py": ("tests/test_admitted_distribution_builder.py",),
    "scripts/build_admitted_distribution.py": (
        "tests/test_admitted_distribution_builder.py",
    ),
    "scripts/build_catalog.py": ("tests/test_asset_documentation.py",),
    "scripts/check.ps1": (
        "tests/test_affected_test_selection.py",
        "tests/test_release_environment.py",
    ),
    "scripts/check_helpers.ps1": ("tests/test_release_environment.py",),
    "scripts/select_affected_tests.py": ("tests/test_affected_test_selection.py",),
    "scripts/validate_asset_documents.py": ("tests/test_asset_documentation.py",),
}

SOURCE_DIRECT_TESTS = {
    "src/scirel/_composition.py": ("tests/test_library_composition.py",),
}

NO_TEST_PREFIXES = (
    "docs/",
    "skills/",
)
NO_TEST_FILES = {
    "AGENTS.md",
    "CONTRIBUTING.md",
    "README.md",
}


@dataclass(frozen=True)
class Asset:
    public_callable: str
    module: str
    source_path: str
    kind: str
    admission_ref: str
    dependency_refs: frozenset[str]
    direct_test: str


def _relative_path(value: str) -> str:
    candidate = Path(value.replace("\\", "/"))
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(ROOT)
        except ValueError as error:
            raise ValueError(f"changed path is outside the SciRel repository: {value}") from error
    normalized = Path(candidate).as_posix()
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"changed path escapes the SciRel repository: {value}")
    return normalized.removeprefix("./")


def _direct_test(public_callable: str, module: str, kind: str) -> str:
    override = DIRECT_TEST_OVERRIDES.get(public_callable)
    if override is not None:
        candidate = override
    else:
        base = module.rsplit(".", 1)[-1]
        if kind == "operator":
            candidate = f"tests/operator_contracts/test_{base}.py"
        else:
            graph_test = f"tests/graph_contracts/{base}/test_graph_{base}.py"
            framework_test = f"tests/framework_compositions/test_{base}.py"
            candidate = graph_test if (ROOT / graph_test).is_file() else framework_test
    if not (ROOT / candidate).is_file():
        raise ValueError(f"no direct test is registered for {public_callable}: {candidate}")
    return candidate


def _load_assets() -> list[Asset]:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assets = []
    for record in ledger["integrations"]:
        public_callable = record["public_callable"]
        module = public_callable.rsplit(".", 1)[0]
        admission = record["admitted_input"]["admission"]
        kind = admission["asset_kind"]
        source_path = "src/" + module.replace(".", "/") + ".py"
        assets.append(
            Asset(
                public_callable=public_callable,
                module=module,
                source_path=source_path,
                kind=kind,
                admission_ref=admission["admission_ref"],
                dependency_refs=frozenset(record["dependency_admission_refs"]),
                direct_test=_direct_test(public_callable, module, kind),
            )
        )
    return assets


def _module_name(path: Path) -> str:
    relative = path.relative_to(ROOT / "src").with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imported_modules(path: Path, module: str) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError):
        return set()
    package = module.split(".") if path.stem == "__init__" else module.split(".")[:-1]
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names if alias.name.startswith("scirel"))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parent_count = node.level - 1
                base = package[: len(package) - parent_count] if parent_count else package
                parts = [*base]
                if node.module:
                    parts.extend(node.module.split("."))
                target = ".".join(parts)
            else:
                target = node.module or ""
            if target.startswith("scirel"):
                imported.add(target)
                imported.update(
                    f"{target}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                )
    return imported


def _reverse_imports() -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = {}
    for path in (ROOT / "src" / "scirel").rglob("*.py"):
        module = _module_name(path)
        for imported in _imported_modules(path, module):
            reverse.setdefault(imported, set()).add(module)
    return reverse


def _module_from_source_path(path: str) -> str:
    relative = Path(path).relative_to("src").with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _dependent_modules(changed_module: str, reverse: dict[str, set[str]]) -> set[str]:
    found = {changed_module}
    queue = [changed_module]
    while queue:
        current = queue.pop()
        for dependent in reverse.get(current, ()):
            if dependent not in found:
                found.add(dependent)
                queue.append(dependent)
    return found


def _dependent_assets(initial: set[Asset], assets: list[Asset]) -> set[Asset]:
    affected = set(initial)
    refs = {asset.admission_ref for asset in affected}
    changed = True
    while changed:
        changed = False
        for asset in assets:
            if asset not in affected and asset.dependency_refs & refs:
                affected.add(asset)
                refs.add(asset.admission_ref)
                changed = True
    return affected


def select(changed_paths: Iterable[str]) -> dict[str, object]:
    assets = _load_assets()
    assets_by_source: dict[str, set[Asset]] = {}
    assets_by_module: dict[str, set[Asset]] = {}
    for asset in assets:
        assets_by_source.setdefault(asset.source_path, set()).add(asset)
        assets_by_module.setdefault(asset.module, set()).add(asset)
    reverse_imports = _reverse_imports()
    normalized = sorted({_relative_path(path) for path in changed_paths})
    tests: set[str] = set()
    affected_assets: set[Asset] = set()
    full_suite_reasons: list[str] = []
    reasons: list[dict[str, object]] = []

    for path in normalized:
        selected_for_path: set[Asset] = set()
        path_tests: set[str] = set()
        reason = ""

        if path in FULL_SUITE_PATHS:
            full_suite_reasons.append(f"{path} changes the test/dependency baseline")
            reason = "full_suite_baseline"
        elif path in ENGINEERING_TESTS:
            path_tests.update(ENGINEERING_TESTS[path])
            reason = "engineering_contract"
        elif path.startswith("contracts/") or path.startswith("catalog/examples/"):
            path_tests.add("tests/test_asset_documentation.py")
            reason = "asset_document_contract"
        elif path in NO_TEST_FILES or path.startswith(NO_TEST_PREFIXES):
            reason = "documentation_only"
        elif path.startswith("tests/"):
            if path == "tests/_review_bindings.py":
                path_tests.update(
                    asset.direct_test for asset in assets if asset.kind == "task_graph"
                )
                reason = "shared_graph_test_support"
            elif (
                Path(path).name.startswith("test_")
                and path.endswith(".py")
                and (ROOT / path).is_file()
            ):
                path_tests.add(path)
                reason = "changed_test"
            elif path.endswith("task_graph.yaml"):
                siblings = sorted((ROOT / path).parent.glob("test_*.py"))
                if siblings:
                    path_tests.update(item.relative_to(ROOT).as_posix() for item in siblings)
                    reason = "changed_graph_contract"
                else:
                    full_suite_reasons.append(f"{path} has no registered graph contract test")
                    reason = "unmapped_test_contract"
            else:
                full_suite_reasons.append(f"{path} changes shared or unmapped test material")
                reason = "shared_test_material"
        elif path.startswith("src/scirel/") and path.endswith("/__init__.py"):
            path_tests.update(
                ("tests/test_asset_documentation.py", "tests/test_public_surface.py")
            )
            reason = "public_exports"
        elif path.startswith("src/scirel/") and path.endswith(".py"):
            path_tests.update(SOURCE_DIRECT_TESTS.get(path, ()))
            selected_for_path.update(assets_by_source.get(path, ()))
            module = _module_from_source_path(path)
            modules = _dependent_modules(module, reverse_imports)
            for item in modules:
                selected_for_path.update(assets_by_module.get(item, ()))
            if not selected_for_path and path.startswith("src/scirel/_framework_compositions/"):
                base = Path(path).stem
                framework_test = f"tests/framework_compositions/test_{base}.py"
                if (ROOT / framework_test).is_file():
                    path_tests.add(framework_test)
                    reason = "framework_composition"
            if selected_for_path:
                selected_for_path = _dependent_assets(selected_for_path, assets)
                affected_assets.update(selected_for_path)
                path_tests.update(asset.direct_test for asset in selected_for_path)
                path_tests.add("tests/test_admitted_integrations.py")
                reason = reason or "asset_and_reverse_dependencies"
            elif not path_tests:
                full_suite_reasons.append(f"{path} is SciRel source without an asset/test mapping")
                reason = "unmapped_scirel_source"
        else:
            full_suite_reasons.append(f"{path} is outside the classified change surfaces")
            reason = "unclassified_change"

        tests.update(path_tests)
        reasons.append(
            {
                "changed_path": path,
                "classification": reason,
                "affected_assets": sorted(asset.public_callable for asset in selected_for_path),
                "tests": sorted(path_tests),
            }
        )

    return {
        "schema": SCHEMA,
        "changed_paths": normalized,
        "full_suite_required": bool(full_suite_reasons),
        "full_suite_reasons": full_suite_reasons,
        "affected_assets": sorted(asset.public_callable for asset in affected_assets),
        "test_paths": ["tests"] if full_suite_reasons else sorted(tests),
        "reasons": reasons,
    }


def _git_paths(base_ref: str | None) -> list[str]:
    if base_ref:
        command = [
            "git",
            "diff",
            "--name-only",
            "-z",
            "--diff-filter=ACMRD",
            f"{base_ref}...HEAD",
        ]
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "git diff failed")
        return [path for path in completed.stdout.split("\0") if path]

    changed = subprocess.run(
        ["git", "diff", "--name-only", "-z", "--diff-filter=ACMRD", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.split("\0")
    untracked = subprocess.run(
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.split("\0")
    return [path for path in (*changed, *untracked) if path]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--base-ref")
    parser.add_argument("--format", choices=("json", "paths"), default="json")
    args = parser.parse_args()
    if args.changed_path and args.base_ref:
        parser.error("use either --changed-path or --base-ref, not both")
    try:
        paths = args.changed_path or _git_paths(args.base_ref)
        result = select(paths)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"affected test selection failed: {error}", file=sys.stderr)
        return 2
    if args.format == "paths":
        print("\n".join(result["test_paths"]))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
