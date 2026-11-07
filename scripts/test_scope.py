#!/usr/bin/env python3
"""Select the deterministic pytest scope for a set of changed paths.

The test tree is organized by functional domain (``tests/<domain>``) plus four
generic layers (``tests/architecture``, ``tests/docs``, ``tests/delivery``,
``tests/tooling``) and one integration suite (``tests/cross_domain``).  This
helper maps changed implementation, contract, tool and documentation paths to
the smallest scope that can observe the change.

Usage::

    python scripts/test_scope.py --changed src/scirel/kinetic/dispersion/rational.py
    python scripts/test_scope.py src/scirel/geometry/field.py catalog/examples/scirel.field.brb.json
    python scripts/test_scope.py            # paths from git (HEAD + untracked)

It prints a runnable ``pytest`` command and never runs the suite itself.  A
path the helper cannot classify makes the whole call fail closed: it prints the
full-suite command and exits non-zero instead of silently under-testing.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
SOURCE = ROOT / "src" / "scirel"

LAYERS = {"architecture", "docs", "delivery", "tooling"}
INTEGRATION = "cross_domain"
FULL_SUITE_EXIT = 2

# Explicit owners include direct tests and layers that exercise a tool through
# another script. New tools must declare their consumers instead of silently
# inheriting tooling/architecture, which misses delivery and docs regressions.
SCRIPT_LAYERS = {
    "acceptance_evidence.py": ("tooling",),
    "audit_public_export_documents.py": ("architecture",),
    "build_capability_matrix.py": ("tooling", "docs", "delivery"),
    "build_catalog.py": ("tooling", "architecture"),
    "build_pure_delivery.py": ("delivery",),
    "build_scirel_sphinx.py": ("docs", "delivery"),
    "capability_catalog.py": ("docs", "delivery"),
    "capability_query.py": ("tooling", "docs", "delivery"),
    "check_wheel_exposure.py": ("delivery",),
    "code_digest.py": ("tooling", "docs", "delivery"),
    "consumer_tools.py": ("delivery",),
    "dev_container.py": ("tooling", "architecture"),
    "exposure.py": ("tooling", "architecture", "docs", "delivery"),
    "export_admission_tools.py": ("delivery",),
    "mapping_interface_bindings.json": ("tooling", "architecture", "docs", "delivery"),
    "measure_capability_runtime.py": ("architecture",),
    "package_catalog_snapshot.py": ("tooling",),
    "prepare_admission.py": ("delivery",),
    "public_api_binding.py": ("tooling", "architecture", "docs", "delivery"),
    "query.py": ("delivery",),
    "solving_skill.py": ("delivery",),
    "review_gate.py": ("tooling",),
    "scirel_docs.py": ("docs", "delivery"),
    "serve_consumer_mcp.py": ("delivery",),
    "test_scope.py": ("tooling",),
    "validate_admission.py": ("delivery",),
    "validate_asset_documents.py": ("tooling", "architecture", "docs", "delivery"),
    "validate_capability_runtime_closure.py": ("architecture",),
    "validate_installed_wheel.py": ("delivery",),
    "validate_overlap_record.py": ("delivery",),
    "validate_runtime_imports.py": ("architecture",),
}
PACKAGING_FILES = {"pyproject.toml", "setup.py", "setup.cfg", "MANIFEST.in"}
GLOBAL_PATHS = {"tests/conftest.py"}
INFRASTRUCTURE_FILES = {".dockerignore", ".gitattributes", ".gitignore"}
INFRASTRUCTURE_PREFIXES = (".githooks/", ".github/", "containers/")
MAINTAINER_DOCS = {"AGENTS.md", "ARCHITECTURE.md", "CONTRIBUTING.md", "README.md", "RULES.md"}
TEST_HARNESS_TARGETS = {
    "tests/_review_bindings.py": ("tests/cross_domain",),
    "tests/fs_links.py": ("tests/delivery", "tests/docs"),
}


class UnresolvedPath(ValueError):
    """A changed path has no deterministic test scope."""


def _layer_target(layer: str) -> str:
    if layer == INTEGRATION:
        return f"tests/{INTEGRATION}"
    return f"tests/{layer}"


def _domain_target(domain: str) -> str:
    if not (TESTS / domain).is_dir():
        raise UnresolvedPath(f"domain {domain!r} has no tests/{domain} directory")
    return f"tests/{domain}"


def _test_dependents(token: str) -> list[str]:
    """Test owners whose modules reference a token (used for split domains).

    A few domains are currently exercised from another domain's or layer's
    directory (for example ``scirel.physics`` from the kinetic algebra-grid
    tests). The scan keeps the mapping deterministic instead of guessing.
    """
    owners = set()
    for path in TESTS.rglob("test_*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if token in text:
            owners.add(path.relative_to(TESTS).parts[0])
    return sorted(owners)


def _domain_scope(domain: str) -> list[str]:
    """Tests that observe a domain, falling back to referencing test owners."""
    if (TESTS / domain).is_dir():
        return [f"tests/{domain}"]
    dependents = [
        owner for owner in _test_dependents(f"scirel.{domain}") if (TESTS / owner).is_dir()
    ]
    if dependents:
        return [f"tests/{owner}" for owner in dependents]
    raise UnresolvedPath(
        f"domain {domain!r} has no tests/{domain} directory and no referencing tests"
    )


def _source_domains() -> set[str]:
    return {
        path.name
        for path in SOURCE.iterdir()
        if path.is_dir() and not path.name.startswith("_") and (path / "__init__.py").is_file()
    }


def _shared_dependents(stem: str) -> list[str]:
    """Domains whose modules mention a shared module stem (conservative)."""
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(stem)}(?![A-Za-z0-9_])")
    domains = set()
    for path in SOURCE.rglob("*.py"):
        relative = path.relative_to(SOURCE)
        if len(relative.parts) < 2 or relative.parts[0].startswith("_"):
            continue
        if path.stem == stem:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if pattern.search(text):
            domains.add(relative.parts[0])
    return sorted(domains)


def _classify_catalog(path: Path) -> tuple[list[str], list[str]]:
    if path.suffix != ".json" or not path.is_file():
        raise UnresolvedPath(f"catalog asset is not a readable JSON file: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        module = document["public_api"]["python"]["module"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise UnresolvedPath(f"catalog asset has no public_api.python.module: {path}") from exc
    if not isinstance(module, str) or not module.startswith("scirel."):
        raise UnresolvedPath(f"catalog asset declares a non-SciRel module: {path}")
    domain = module.split(".")[1]
    return [*_domain_scope(domain), _layer_target("docs")], [
        "catalog is the documentation truth source"
    ]


def _classify_tests(relative: Path) -> tuple[list[str], list[str]]:
    parts = relative.parts
    if parts and parts[0] == "fixtures":
        owners = [
            owner
            for owner in _test_dependents(relative.name)
            if owner != "fixtures" and (TESTS / owner).is_dir()
        ]
        if owners:
            return [f"tests/{owner}" for owner in owners], [
                "shared fixture: referencing test owners"
            ]
        raise UnresolvedPath(f"shared fixture has no referencing tests: {relative}")
    if len(parts) < 2:
        owners = [owner for owner in _test_dependents(parts[0]) if (TESTS / owner).is_dir()]
        if owners:
            return [f"tests/{owner}" for owner in owners], ["shared test fixture"]
        raise UnresolvedPath(
            f"file directly under tests/ is not owned by a layer or domain: {relative}"
        )
    owner = parts[0]
    if owner in LAYERS:
        return [_layer_target(owner)], []
    if owner == INTEGRATION:
        return [_layer_target(INTEGRATION)], []
    return [_domain_target(owner)], []


def _classify_script(name: str) -> tuple[list[str], list[str]]:
    if name == "review_harness.py":
        return _review_scope(), ["held contract tests and review harness boundaries"]
    if name == "build_pleiades_truth.py":
        return ["tests/cross_domain/multi_coil_vacuum_field"], [
            "downstream truth consumers only: pytest does not execute the external source generator; "
            "regeneration requires the explicitly supplied external source"
        ]
    if name not in SCRIPT_LAYERS:
        raise UnresolvedPath(f"script has no declared test consumers: scripts/{name}")
    return [_layer_target(layer) for layer in SCRIPT_LAYERS[name]], []


def _review_scope(module: str | None = None, asset_id: str | None = None) -> list[str]:
    from review_harness import load_review_documents, review_test_references

    try:
        documents = load_review_documents(ROOT)
        if module is not None:
            documents = [
                document
                for document in documents
                if document["public_api"]["python"]["module"] == module
                or document["public_api"]["python"]["module"].startswith(module + ".")
            ]
        if asset_id is not None:
            documents = [document for document in documents if document["asset_id"] == asset_id]
        if (module is not None or asset_id is not None) and not documents:
            raise ValueError("review candidate has no held contract binding")
        tests = review_test_references(documents, ROOT)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise UnresolvedPath(str(error)) from error
    return [*tests, _layer_target("tooling"), _layer_target("architecture")]


def classify(relative: Path) -> tuple[list[str], list[str]]:
    """Map one repository-relative path to pytest targets and notes."""
    parts = relative.parts
    if not parts:
        raise UnresolvedPath("empty path")

    if relative.as_posix() in GLOBAL_PATHS:
        return ["<full-suite>"], ["global test configuration affects every scope"]
    if relative.as_posix() in INFRASTRUCTURE_FILES or relative.as_posix().startswith(
        INFRASTRUCTURE_PREFIXES
    ):
        return [_layer_target("tooling"), _layer_target("architecture")], [
            "development infrastructure changes hooks, CI, containers or checkout metadata"
        ]
    if relative.as_posix() in MAINTAINER_DOCS:
        return [_layer_target("architecture"), _layer_target("docs")], [
            "maintainer-facing repository rules"
        ]
    if relative.as_posix() in TEST_HARNESS_TARGETS:
        return list(TEST_HARNESS_TARGETS[relative.as_posix()]), ["shared test harness"]

    if parts[0] == "tests":
        return _classify_tests(Path(*parts[1:]))

    if parts[0] == "catalog":
        if parts[1:5] == ("review", "candidates", "src", "scirel") and relative.suffix == ".py":
            module_parts = list(parts[4:-1])
            if relative.stem != "__init__":
                module_parts.append(relative.stem)
            return _review_scope(module=".".join(module_parts)), [
                "held implementation: tests bound by its review contract"
            ]
        if len(parts) == 4 and parts[1:3] == ("review", "examples") and relative.suffix == ".json":
            return _review_scope(asset_id=relative.stem), [
                "held contract: direct tests and review boundaries"
            ]
        if len(parts) >= 3 and parts[1] == "examples":
            targets, notes = _classify_catalog(ROOT / relative)
            notes.append(
                f"validate the asset: python scripts/validate_asset_documents.py {relative}"
            )
            return targets, notes
        return [_layer_target("tooling"), _layer_target("architecture")], [
            "catalog tooling changes are covered by the tooling and architecture layers"
        ]

    if parts[0] == "tools":
        if len(parts) >= 2 and parts[1] == "docs":
            return [_layer_target("docs")], ["handbook pipeline change"]
        return [_layer_target("tooling"), _layer_target("architecture")], []

    if parts[0] == "contracts":
        if len(parts) >= 2 and parts[1] in {"admission", "reception"}:
            return [_layer_target("delivery")], ["admission/reception contract"]
        return [
            _layer_target("architecture"),
            _layer_target("tooling"),
            _layer_target("docs"),
        ], [
            "asset schema change: affected domains are not derivable, run the full suite before merge"
        ]

    if parts[0] == "scripts":
        if len(parts) != 2:
            raise UnresolvedPath(f"script path has no declared test consumers: {relative}")
        return _classify_script(parts[1])

    if parts[:4] == ("skills", "development", "usage", "scirel-solving"):
        return [_layer_target("delivery")], [
            "solving source projection and helper closure; scientific task acceptance is separate"
        ]

    if parts[0] == "licenses":
        return [_layer_target("delivery")], ["license files are part of the wheel contract"]

    if len(parts) == 1 and parts[0] in PACKAGING_FILES:
        if parts[0] == "pyproject.toml":
            return [_layer_target("architecture"), _layer_target("delivery")], [
                "project metadata/pytest/dependency change: architecture + installed-wheel layers; "
                "dependency changes can affect every domain"
            ]
        return [_layer_target("delivery")], ["packaging change"]

    if parts[0] == "src" and len(parts) >= 3 and parts[1] == "scirel":
        remainder = parts[2:]
        head = remainder[0]
        if head == "__init__.py":
            return [_layer_target("architecture"), _layer_target(INTEGRATION)], [
                "root public namespace"
            ]
        if head == "_framework_compositions":
            return [_domain_target("framework_compositions"), _layer_target("architecture")], []
        if head.startswith("_") or head.endswith(".py"):
            stem = Path(head).stem
            dependents = [
                domain for domain in _shared_dependents(stem) if (TESTS / domain).is_dir()
            ]
            targets = [_layer_target("architecture"), _layer_target(INTEGRATION)]
            targets.extend(_domain_target(domain) for domain in dependents)
            notes = ["shared implementation module"]
            if dependents:
                notes.append("imported by: " + ", ".join(dependents))
            return targets, notes
        if not (SOURCE / head / "__init__.py").is_file():
            raise UnresolvedPath(f"{relative} is not below a public domain package")
        if head not in _source_domains():
            raise UnresolvedPath(f"unknown domain {head!r}")
        if remainder[-1] == "__init__.py":
            return [_layer_target("architecture"), *_domain_scope(head)], ["public package facade"]
        return _domain_scope(head), []

    if relative.suffix == ".md":
        return [_layer_target("docs")], ["documentation layer"]

    raise UnresolvedPath(f"no deterministic test scope for {relative}")


def _normalize(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    try:
        return path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise UnresolvedPath(f"path is outside the repository: {raw}") from exc


def _git_name_only(arguments: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", *arguments, "-z"],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"cannot read changes from git: {result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return [
        entry for entry in result.stdout.decode("utf-8", "surrogateescape").split("\0") if entry
    ]


def _git_changed_paths() -> list[str]:
    paths = _git_name_only(["diff", "--name-only", "HEAD"])
    paths.extend(_git_name_only(["ls-files", "--others", "--exclude-standard"]))
    return sorted(set(paths))


def _render(targets: list[str], notes: list[str]) -> str:
    lines = [f"  {note}" for note in notes]
    if "<full-suite>" in targets:
        command = f"{sys.executable} -m pytest -q"
    else:
        command = f"{sys.executable} -m pytest -q " + " ".join(targets)
    lines.append("Run:")
    lines.append(f"  {command}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="changed paths (repository-relative)")
    parser.add_argument(
        "--changed",
        nargs="+",
        action="extend",
        default=None,
        help="changed paths, same as positional arguments",
    )
    args = parser.parse_args(argv)
    raw_paths = [*args.paths, *(args.changed or [])]
    if not raw_paths:
        raw_paths = _git_changed_paths()
    if not raw_paths:
        print("No changed paths: nothing to select.")
        return 0

    targets: set[str] = set()
    notes: list[str] = []
    unresolved: list[str] = []
    for raw in sorted(set(raw_paths)):
        try:
            relative = _normalize(raw)
            path_targets, path_notes = classify(relative)
        except UnresolvedPath as exc:
            unresolved.append(str(exc))
            continue
        targets.update(path_targets)
        notes.extend(f"{relative}: {note}" for note in path_notes)

    if unresolved:
        print("FAIL-CLOSED: at least one changed path has no deterministic scope:")
        for message in unresolved:
            print(f"  - {message}")
        partial = sorted(target for target in targets if target != "<full-suite>")
        if partial:
            print("Resolved partial scope:")
            print("  " + " ".join(partial))
        print("Full suite (required until the mapping is extended):")
        print(f"  {sys.executable} -m pytest -q")
        return FULL_SUITE_EXIT

    print(f"Selected scope for {len(raw_paths)} changed path(s):")
    print(_render(sorted(targets), notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
