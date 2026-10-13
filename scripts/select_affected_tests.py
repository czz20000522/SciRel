"""Select SciRel tests from changed files and exact asset dependencies."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, replace
import json
from pathlib import Path
import subprocess
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "provenance" / "admitted-assets.json"
CATALOG = ROOT / "catalog" / "examples"
# A bounded D2 family can be indexed without mutating the historical pilot.
# Keep this explicit rather than recursively globbing every future worktree.
PLEIADES_MAINTAINED_CATALOG = ROOT / "catalog" / "pleiades-maintained"
TORAX_LEAF_CATALOG = ROOT / "catalog" / "torax-algebra-grid"
TORAX_BOOTSTRAP_FVM_CATALOG = ROOT / "catalog" / "torax-bootstrap-fvm"
SCHEMA = "scirel.affected-tests.v1"

DIRECT_TEST_OVERRIDES = {
    "scirel.inference.anisotropic_trial_evaluation.evaluate_anisotropic_trial": (
        "tests/test_incremental_admissions.py"
    ),
}

FULL_SUITE_PATHS = {
    "pyproject.toml",
}

EXTERNAL_TOOLING_TESTS = {
    "scripts/build_extraction_skill_bundle.py": "skills/extraction/tests/test_extraction_skill_bundle.py",
    "scripts/install_extraction_skill_bundle.py": "skills/extraction/tests/test_extraction_skill_bundle.py",
    "skills/extraction/tests/test_extraction_skill_bundle.py": "skills/extraction/tests/test_extraction_skill_bundle.py",
    "scripts/build_admitted_distribution.py": "provenance/tests/test_admitted_distribution_builder.py",
    "provenance/admitted-assets.json": "provenance/tests/test_admitted_distribution_builder.py",
    "provenance/tests/test_admitted_distribution_builder.py": "provenance/tests/test_admitted_distribution_builder.py",
}

ENGINEERING_TESTS = {
    "docs/integration/codefusion-consumer-contract.md": (
        "tests/test_codefusion_consumer_contract.py",
    ),
    "docs/design/scientific-request-workflow.md": (
        "tests/test_scientific_request_workflow_docs.py",
    ),
    "docs/requirements/scientific-request-workflow.md": (
        "tests/test_scientific_request_workflow_docs.py",
    ),
    "skills/usage/scirel-solving/SKILL.md": (
        "tests/test_scientific_request_workflow_docs.py",
    ),
    "skills/usage/scirel-solving/references/thin-adapter-run.md": (
        "tests/test_scientific_request_workflow_docs.py",
    ),
    "skills/usage/scientific-asset-navigation/SKILL.md": (
        "tests/test_scientific_request_workflow_docs.py",
    ),
    "skills/usage/scientific-project-implementation/SKILL.md": (
        "tests/test_scientific_request_workflow_docs.py",
    ),
    "examples/user_acceptance.py": ("tests/test_user_acceptance.py",),
    "scripts/build_catalog.py": ("tests/test_asset_documentation.py",),
    "scripts/scirel_docs.py": ("tests/test_scirel_docs.py",),
    "scripts/build_scirel_sphinx.py": ("tests/test_scirel_docs.py",),
    "tests/_document_fixtures.py": (
        "tests/test_asset_documentation.py", "tests/test_thin_mcp_adapter.py",
        "tests/test_scirel_docs.py",
    ),
    "scripts/finalize_release.py": (
        "tests/test_release_finalization.py", "tests/test_release_index.py",
    ),
    "scripts/verify_review_selection.py": ("tests/test_review_selection.py",),
    "scripts/prepare_reviewed_distribution.py": (
        "tests/test_release_environment.py", "tests/test_release_index.py",
    ),
    "scripts/release_index.py": ("tests/test_release_index.py",),
    "provenance/release-index.dev.json": ("tests/test_release_index.py",),
    "contracts/release-index-dev.schema.json": ("tests/test_release_index.py",),
    "contracts/reviewed-release-manifest-dev.schema.json": (
        "tests/test_release_index.py",
    ),
    "scripts/check.ps1": (
        "tests/test_affected_test_selection.py",
        "tests/test_release_environment.py",
        "tests/test_release_finalization.py",
        "tests/test_release_index.py",
    ),
    "scripts/check_helpers.ps1": ("tests/test_release_environment.py",),
    "scripts/select_affected_tests.py": ("tests/test_affected_test_selection.py",),
    "scripts/build_l1_inventory.py": ("tests/workflow/test_l1_inventory.py",),
    "scripts/build_l1_wire_fixture.py": ("tests/test_l1_wire_smoke.py",),
    "scripts/run_l1_wire_smoke.py": ("tests/test_l1_wire_smoke.py",),
    "scripts/build_l1_bundle.py": ("tests/workflow/test_l1_bundle.py",),
    "scripts/submit_standardization.py": (
        "tests/workflow/test_standardization_submission.py",
        "tests/test_workflow_contracts.py",
    ),
    "scripts/verify_outbound_evaluation_manifests.py": (
        "tests/test_outbound_evaluation_manifests.py",
    ),
    "scripts/run_scirel_https.py": ("tests/plugin/test_http_listener.py",),
    "scripts/validate_asset_documents.py": ("tests/test_asset_documentation.py",),
}

WORKFLOW_TESTS = (
    "tests/workflow/test_workflow.py",
    "tests/workflow/test_vertical_slice.py",
    "tests/workflow/test_l1_inventory.py",
    "tests/workflow/test_l1_bundle.py",
    "tests/workflow/test_standardization_submission.py",
    "tests/test_workflow_contracts.py",
)

PLUGIN_TESTS = (
    "tests/plugin/test_codefusion_plugin_contract.py",
    "tests/plugin/test_http_listener.py",
    "tests/workflow/test_vertical_slice.py",
)

WORKFLOW_CONTRACTS = {
    "contracts/body-wire-request-dev.schema.json",
    "contracts/candidate-package-dev.schema.json",
    "contracts/automated-check-result-dev.schema.json",
    "contracts/l1-bundle-dev.schema.json",
    "contracts/l1-inventory-dev.schema.json",
    "contracts/standardized-draft-dev.schema.json",
    "contracts/standardization-submission-dev.schema.json",
    "contracts/review-decision-dev.schema.json",
    "contracts/review-item-dev.schema.json",
    "contracts/review-item-decision-dev.schema.json",
    "contracts/review-item-detail-dev.schema.json",
    "contracts/review-completed-results-dev.schema.json",
    "contracts/release-manifest-dev.schema.json",
    "contracts/review-ui-extension-dev.schema.json",
    "contracts/workflow-state-dev.schema.json",
}

SOURCE_DIRECT_TESTS = {
    "src/scirel/_composition.py": ("tests/test_library_composition.py",),
    "src/scirel_adapter/__init__.py": ("tests/test_thin_mcp_adapter.py",),
    "src/scirel_adapter/mcp.py": ("tests/test_thin_mcp_adapter.py",),
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
    asset_ref: str
    dependency_refs: frozenset[str]
    direct_tests: tuple[str, ...]


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


def _load_ledger_assets() -> list[Asset]:
    """Load the historical admission ledger, kept as a compatibility input.

    The ledger still binds the 52 migrated development assets to their callables
    and direct tests.  It is no longer the admission authority: assets that now
    carry a canonical catalog document are loaded from that document instead.
    """
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
                asset_ref=admission["admission_ref"],
                dependency_refs=frozenset(record["dependency_admission_refs"]),
                direct_tests=(_direct_test(public_callable, module, kind),),
            )
        )
    return assets


def _load_catalog_assets() -> list[Asset]:
    """Load the canonical exact documents as the current asset index.

    A document is the current authority for one scientific identity: it names the
    public callable, the direct tests that keep the contract verified, and the
    dependency closure of a TaskGraph.  Reading them here keeps affected-test
    selection aligned with the same source the catalog is built from, and it does
    not reintroduce admission or review records into the public contract.
    """
    if not CATALOG.is_dir():
        return []
    assets = []
    catalog_paths = list(CATALOG.glob("*.json"))
    if CATALOG == ROOT / "catalog" / "examples":
        catalog_paths.extend(PLEIADES_MAINTAINED_CATALOG.glob("*.json"))
        catalog_paths.extend(TORAX_LEAF_CATALOG.glob("*.json"))
        catalog_paths.extend(TORAX_BOOTSTRAP_FVM_CATALOG.glob("*.json"))
    for path in sorted(catalog_paths):
        document = json.loads(path.read_text(encoding="utf-8"))
        python_api = document["public_api"]["python"]
        module = python_api["module"]
        symbol = python_api["symbol"]
        implementation_module = _exported_module(module, symbol)
        direct_tests = tuple(document["verification"]["tests"])
        for direct_test in direct_tests:
            if not (ROOT / direct_test).is_file():
                raise ValueError(f"{path.name} declares a missing direct test: {direct_test}")
        assets.append(
            Asset(
                public_callable=f"{module}.{symbol}",
                module=implementation_module,
                source_path="src/" + implementation_module.replace(".", "/") + ".py",
                kind=document["kind"],
                asset_ref=document["asset_id"],
                dependency_refs=frozenset(
                    entry["asset_id"]
                    for entry in document["version"]["dependencies"]
                ),
                direct_tests=direct_tests,
            )
        )
    return assets


def _exported_module(module: str, symbol: str) -> str:
    """Resolve an explicit package re-export without importing scientific code."""
    initializer = ROOT / "src" / Path(*module.split(".")) / "__init__.py"
    if not initializer.is_file():
        return module
    tree = ast.parse(initializer.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any(
            (alias.asname or alias.name) == symbol for alias in node.names
        ):
            base = module.split(".")
            if node.level:
                base = base[:len(base) - node.level + 1]
                return ".".join([*base, *(node.module or "").split(".")])
            return node.module or module
    return module


def _load_assets() -> list[Asset]:
    """Union current documents with legacy samples under one dependency ID space."""
    catalog = _load_catalog_assets()
    catalog_by_callable = {asset.public_callable: asset for asset in catalog}
    ledger_assets = _load_ledger_assets()
    legacy_to_current_ref = {
        asset.asset_ref: catalog_by_callable.get(asset.public_callable, asset).asset_ref
        for asset in ledger_assets
    }
    ledger = [
        replace(
            asset,
            dependency_refs=frozenset(
                legacy_to_current_ref.get(reference, reference)
                for reference in asset.dependency_refs
            ),
        )
        for asset in ledger_assets
        if asset.public_callable not in catalog_by_callable
    ]
    return [*ledger, *catalog]


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
                resolved = {
                    _exported_module(target, alias.name)
                    for alias in node.names if alias.name != "*"
                }
                imported.update(resolved)
                if any(alias.name == "*" for alias in node.names) or not resolved:
                    imported.add(target)
    return imported


def _reverse_imports() -> dict[str, set[str]]:
    reverse: dict[str, set[str]] = {}
    for path in (ROOT / "src" / "scirel").rglob("*.py"):
        # Namespace re-exports are resolved at the consuming symbol above.
        # Their initializer's body is checked separately for export changes;
        # a changed leaf must not connect every unrelated package export.
        if path.name == "__init__.py":
            continue
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
    refs = {asset.asset_ref for asset in affected}
    changed = True
    while changed:
        changed = False
        for asset in assets:
            if asset not in affected and asset.dependency_refs & refs:
                affected.add(asset)
                refs.add(asset.asset_ref)
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

        if path in EXTERNAL_TOOLING_TESTS:
            path_tests.add(EXTERNAL_TOOLING_TESTS[path])
            reason = "external_tooling"
        elif path.startswith(("skills/extraction/", "provenance/tests/")):
            reason = "external_tooling"
        elif path in FULL_SUITE_PATHS:
            full_suite_reasons.append(f"{path} changes the test/dependency baseline")
            reason = "full_suite_baseline"
        elif path in ENGINEERING_TESTS:
            path_tests.update(ENGINEERING_TESTS[path])
            reason = "engineering_contract"
        elif path.startswith("tools/docs/"):
            path_tests.add("tests/test_scirel_docs.py")
            reason = "documentation_contract"
        elif path in WORKFLOW_CONTRACTS:
            path_tests.update((*WORKFLOW_TESTS, *PLUGIN_TESTS))
            reason = "workflow_contract"
        elif path.startswith("docs/evaluations/outbound-progressive-projects/manifests/"):
            path_tests.add("tests/test_outbound_evaluation_manifests.py")
            reason = "evaluation_manifest_contract"
        elif path.startswith("contracts/") or path.startswith(
            ("catalog/examples/", "catalog/pleiades-maintained/", "catalog/torax-algebra-grid/", "catalog/torax-bootstrap-fvm/")
        ):
            path_tests.add("tests/test_asset_documentation.py")
            reason = "asset_document_contract"
        elif path in NO_TEST_FILES or path.startswith(NO_TEST_PREFIXES):
            reason = "documentation_only"
        elif path.startswith("tests/fixtures/l1/"):
            path_tests.update(
                (
                    "tests/test_l1_wire_smoke.py",
                    "tests/workflow/test_vertical_slice.py",
                )
            )
            reason = "workflow_fixture"
        elif path.startswith("tests/"):
            if path == "tests/_review_bindings.py":
                path_tests.update(
                    test
                    for asset in assets
                    if asset.kind == "task_graph"
                    for test in asset.direct_tests
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
        elif path.startswith("src/scirel_workflow/") and path.endswith(".py"):
            path_tests.update(WORKFLOW_TESTS)
            reason = "workflow_source_contract"
        elif path.startswith("src/scirel_plugin/") and path.endswith(".py"):
            path_tests.update(PLUGIN_TESTS)
            if path.endswith("plugin.py"):
                path_tests.update(WORKFLOW_TESTS)
            reason = "plugin_source_contract"
        elif path.startswith("src/scirel_adapter/") and path.endswith(".py"):
            path_tests.update(SOURCE_DIRECT_TESTS.get(path, ()))
            if path_tests:
                reason = "source_engineering_contract"
            else:
                full_suite_reasons.append(
                    f"{path} is adapter source without a test mapping"
                )
                reason = "unmapped_adapter_source"
        elif path.startswith("src/scirel/") and path.endswith("/__init__.py"):
            path_tests.update(
                ("tests/test_asset_documentation.py", "tests/test_public_surface.py")
            )
            if path == "src/scirel/collisions/__init__.py":
                path_tests.add("tests/operator_contracts/test_momentum_scales.py")
            reason = "public_exports"
        elif path.startswith("src/scirel/") and path.endswith(".py"):
            direct_source_tests = SOURCE_DIRECT_TESTS.get(path, ())
            path_tests.update(direct_source_tests)
            if direct_source_tests:
                reason = "source_engineering_contract"
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
                path_tests.update(
                    test for asset in selected_for_path for test in asset.direct_tests
                )
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
