"""Suggest an expert review scope from exact frozen development snapshots.

This is a read-only change/impact report, not a scientific equivalence or approval gate.
"""

from __future__ import annotations

import argparse
import ast
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
import zipfile

from finalize_release import _validate_catalog
from select_affected_tests import ROOT, select


SCHEMA = "scirel.review-scope.dev"


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("snapshot artifact path is missing")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"snapshot artifact is missing or escapes its root: {relative}")
    return path


def _read_snapshot(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    manifest_bytes = _snapshot_file(root, "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    if manifest.get("schema") != "scirel.review-version.dev":
        raise ValueError("unsupported review snapshot schema")
    if not isinstance(manifest.get("git_commit"), str) or not re.fullmatch(
        r"[0-9a-f]{40}", manifest["git_commit"]
    ):
        raise ValueError("review snapshot has an invalid Git commit")
    catalog = _validate_catalog(root / "catalog")
    if (
        manifest["catalog"].get("path") != "catalog/release.json"
        or manifest["catalog"].get("root_digest") != catalog["root_digest"]
        or manifest["catalog"].get("coverage") != catalog["coverage"]
    ):
        raise ValueError("review snapshot catalog differs from its manifest")
    entries = [
        *manifest["exact_documents"],
        manifest["review_dossier"],
        manifest["test_evidence"],
        manifest["wheel"],
    ]
    materials = manifest.get("review_materials", [])
    if not isinstance(materials, list):
        raise ValueError("review snapshot materials must be a list")
    material_paths = set()
    for entry in materials:
        if not isinstance(entry, dict):
            raise ValueError("review snapshot has an invalid material entry")
        relative = entry.get("path")
        if (
            not isinstance(relative, str)
            or not relative.startswith("docs/")
            or not relative.endswith(".md")
            or relative in material_paths
            or entry.get("snapshot_path") != f"review-materials/{relative}"
        ):
            raise ValueError("review snapshot has an invalid material entry")
        material_paths.add(relative)
    entries.extend(materials)
    for entry in entries:
        path = _snapshot_file(root, entry.get("snapshot_path", entry.get("path")))
        if _sha256(path) != entry["sha256"]:
            raise ValueError(f"snapshot artifact digest differs: {path}")
    documents = {}
    for entry in manifest["exact_documents"]:
        document = json.loads(_snapshot_file(root, entry["snapshot_path"]).read_text(encoding="utf-8"))
        asset_id = document["asset_id"]
        if asset_id in documents:
            raise ValueError(f"snapshot repeats asset ID: {asset_id}")
        documents[asset_id] = document
    if len(documents) != manifest["catalog"]["coverage"]["included_asset_count"]:
        raise ValueError("snapshot document count differs from catalog coverage")
    catalog_records = {}
    for path in (root / "catalog" / "records").rglob("*.json"):
        record = json.loads(
            _snapshot_file(root, path.relative_to(root).as_posix()).read_text(encoding="utf-8")
        )
        asset_id = record["asset_id"]
        if asset_id in catalog_records:
            raise ValueError(f"catalog repeats asset ID: {asset_id}")
        catalog_records[asset_id] = record
    if catalog_records != documents:
        raise ValueError("catalog records differ from exact documents")
    return manifest, documents, manifest_digest


def _scientific_document(document: dict[str, Any]) -> dict[str, Any]:
    comparable = {**document, "version": dict(document["version"])}
    comparable["version"].pop("implementation_version", None)
    return comparable


def _wheel_environment(
    root: Path, manifest: dict[str, Any]
) -> tuple[str | None, tuple[str, ...]]:
    with zipfile.ZipFile(_snapshot_file(root, manifest["wheel"]["path"])) as archive:
        metadata_paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            raise ValueError("review wheel must contain exactly one distribution METADATA")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
    if metadata.get("Name", "").lower().replace("_", "-") != "scirel":
        raise ValueError("review wheel distribution is not scirel")
    requirements = tuple(sorted(metadata.get_all("Requires-Dist", [])))
    return metadata.get("Requires-Python"), requirements


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=True
    )
    return result.stdout.decode("utf-8").strip()


def _git_show(commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=True
    )
    return result.stdout.decode("utf-8")


def _public_export_surface(
    source: str, package: str
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]], list[str] | None, str] | None:
    """Parse one ``__init__.py`` into ordered export bindings and a residual AST dump.

    Returns ``(bindings, other_bindings, all_names, residual)`` where
    ``bindings`` is the ordered list of ``(module, symbol, local_name)`` triples
    for ``scirel.*`` imports, ``other_bindings`` the same for non-``scirel``
    imports, ``all_names`` the literal ``__all__`` list or ``None`` when absent,
    and ``residual`` the AST dump with the import and ``__all__`` statements
    removed.  Returns ``None`` for anything this parser refuses to judge:
    syntax errors, star imports, dynamic ``__all__``, or a local name bound
    more than once (a duplicate or shadowed alias cannot be attributed).
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    bindings: list[tuple[str, str, str]] = []
    other_bindings: list[tuple[str, str, str]] = []
    all_names: list[str] | None = None
    seen_all = 0
    seen_locals: set[str] = set()
    body = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                drop = node.level - 1
                if drop > len(parts):
                    return None
                base = parts[: len(parts) - drop] if drop else parts
                target = ".".join(
                    [*base, *(node.module.split(".") if node.module else [])]
                )
            else:
                target = node.module or ""
            if any(alias.name == "*" for alias in node.names):
                return None
            for alias in node.names:
                local = alias.asname or alias.name
                if local in seen_locals:
                    return None
                seen_locals.add(local)
                entry = (target, alias.name, local)
                if target.startswith("scirel"):
                    bindings.append(entry)
                else:
                    other_bindings.append(entry)
            continue
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
        ):
            seen_all += 1
            if seen_all > 1 or not isinstance(node.value, (ast.List, ast.Tuple)):
                return None
            names = []
            for element in node.value.elts:
                if not isinstance(element, ast.Constant) or not isinstance(
                    element.value, str
                ):
                    return None
                names.append(element.value)
            all_names = names
            continue
        body.append(node)
    if seen_all and all_names is None:
        return None
    tree.body = body
    return bindings, other_bindings, all_names, ast.dump(tree)


def _attributed_export_assets(
    path: str, baseline_commit: str, candidate_commit: str, by_callable: dict[str, str]
) -> set[str] | None:
    """Attribute a pure public-export change in an ``__init__.py`` to assets.

    Compares the two frozen blob versions at the AST level, modelling exports
    as ordered ``(module, symbol, local_name)`` triples so that alias
    rebinding, duplicate aliases and import reordering are visible.  The change
    is a pure export change only when the residual AST (everything except
    import statements and the ``__all__`` literal) is identical, no
    non-``scirel`` import changed, the import and ``__all__`` orderings change
    only by additions and removals (never reorders), and every added or
    removed symbol resolves through that version's own imports to a callable of
    a known asset.  Returns the mapped asset IDs, or ``None`` when the change
    is not machine-verifiably a pure export change -- the caller must then keep
    the fail-closed behaviour.
    """
    parts = Path(path).parts
    if len(parts) < 3 or parts[-1] != "__init__.py":
        return None
    package = ".".join(parts[1:-1])
    try:
        before = _public_export_surface(_git_show(baseline_commit, path), package)
        after = _public_export_surface(_git_show(candidate_commit, path), package)
    except (OSError, ValueError, subprocess.CalledProcessError, UnicodeDecodeError):
        return None
    if before is None or after is None:
        return None
    before_bindings, before_other, before_all, before_residual = before
    after_bindings, after_other, after_all, after_residual = after
    if before_residual != after_residual or before_other != after_other:
        return None
    if (before_all is None) != (after_all is None):
        return None
    removed = [entry for entry in before_bindings if entry not in after_bindings]
    added = [entry for entry in after_bindings if entry not in before_bindings]
    if [entry for entry in before_bindings if entry not in removed] != [
        entry for entry in after_bindings if entry not in added
    ]:
        return None
    removed_names = [name for name in before_all or [] if name not in after_all or []]
    added_names = [name for name in after_all or [] if name not in before_all or []]
    if [name for name in before_all or [] if name not in removed_names] != [
        name for name in after_all or [] if name not in added_names
    ]:
        return None
    assets = set()
    for module, symbol, _local in [*removed, *added]:
        asset_id = by_callable.get(f"{module}.{symbol}")
        if asset_id is None:
            return None
        assets.add(asset_id)
    after_by_local = {local: (module, symbol) for module, symbol, local in after_bindings}
    before_by_local = {local: (module, symbol) for module, symbol, local in before_bindings}
    for name in added_names:
        module, symbol = after_by_local.get(name, (None, None))
        asset_id = by_callable.get(f"{module}.{symbol}") if module else None
        if asset_id is None:
            return None
        assets.add(asset_id)
    for name in removed_names:
        module, symbol = before_by_local.get(name, (None, None))
        asset_id = by_callable.get(f"{module}.{symbol}") if module else None
        if asset_id is None:
            return None
        assets.add(asset_id)
    return assets


def _changed_paths(baseline_commit: str, candidate_commit: str) -> list[str]:
    output = subprocess.run(
        [
            "git", "-c", "core.quotepath=false", "diff", "--name-only", "-z",
            "--diff-filter=ACMRD", baseline_commit, candidate_commit, "--",
        ],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    return sorted(path for path in output.decode("utf-8").split("\0") if path)


def _source_impact(
    paths: list[str],
    baseline_commit: str,
    candidate_commit: str,
    documents: dict[str, dict[str, Any]],
) -> tuple[set[str], list[str]]:
    if not paths:
        return set(), []
    if _git("rev-parse", "HEAD") != candidate_commit or _git("status", "--porcelain"):
        raise ValueError("source impact requires a clean checkout at the candidate commit")
    selection = select(paths)
    by_callable = {
        f"{document['public_api']['python']['module']}.{document['public_api']['python']['symbol']}": asset_id
        for asset_id, document in documents.items()
    }
    affected = set()
    unresolved = []
    for reason in selection["reasons"]:
        callables = reason["affected_assets"]
        if callables:
            if any(item not in by_callable for item in callables):
                unresolved.append(reason["changed_path"])
            else:
                affected.update(by_callable[item] for item in callables)
            continue
        # An __init__.py export change is unattributable to the selector, but a
        # pure, machine-verifiable public-export change is attributed here to
        # exactly the assets whose callables entered or left the surface; every
        # other shape stays fail-closed via the unresolved path below.
        if reason.get("classification") == "public_exports":
            attributed = _attributed_export_assets(
                reason["changed_path"], baseline_commit, candidate_commit, by_callable
            )
            if attributed is not None:
                affected.update(attributed)
                continue
        unresolved.append(reason["changed_path"])
    if selection["full_suite_required"] or unresolved:
        affected.update(documents)
    return affected, unresolved


def _reverse_dependents(
    seeds: set[str], documents: dict[str, dict[str, Any]]
) -> set[str]:
    reverse: dict[str, set[str]] = {}
    for asset_id, document in documents.items():
        for dependency in document["version"]["dependencies"]:
            reverse.setdefault(dependency["asset_id"], set()).add(asset_id)
    affected = set(seeds)
    queue = list(seeds)
    while queue:
        for dependent in reverse.get(queue.pop(), ()):
            if dependent not in affected:
                affected.add(dependent)
                queue.append(dependent)
    return affected


def review_scope(candidate_dir: Path, baseline_dir: Path | None = None) -> dict[str, Any]:
    candidate, current, candidate_manifest_digest = _read_snapshot(candidate_dir)
    if baseline_dir is None:
        return {
            "schema": SCHEMA,
            "mode": "first_review",
            "candidate_commit": candidate["git_commit"],
            "candidate_manifest_digest": candidate_manifest_digest,
            "comparison_commit": None,
            "comparison_manifest_digest": None,
            "baseline_approval_verified": False,
            "runtime_requirements_changed": None,
            "review_asset_ids": sorted(current),
            "changed_document_ids": sorted(current),
            "mechanical_only_document_ids": [],
            "removed_asset_ids": [],
            "changed_paths": [],
            "unresolved_source_paths": [],
            "removed_assets_require_manual_review": False,
        }

    baseline, previous, comparison_manifest_digest = _read_snapshot(baseline_dir)
    runtime_requirements_changed = _wheel_environment(
        candidate_dir, candidate
    ) != _wheel_environment(baseline_dir, baseline)
    changed = {
        asset_id for asset_id, document in current.items()
        if asset_id not in previous
        or _scientific_document(document) != _scientific_document(previous[asset_id])
    }
    mechanical = {
        asset_id for asset_id, document in current.items()
        if asset_id in previous
        and document != previous[asset_id]
        and _scientific_document(document) == _scientific_document(previous[asset_id])
    }
    changed_paths = _changed_paths(baseline["git_commit"], candidate["git_commit"])
    source_paths = [
        path for path in changed_paths
        if path.startswith("src/scirel/") and path.endswith(".py")
    ]
    source_assets, unresolved = _source_impact(
        source_paths, baseline["git_commit"], candidate["git_commit"], current
    )
    changed_tests = {path for path in changed_paths if path.startswith("tests/")}
    evidence_assets = {
        asset_id for asset_id, document in current.items()
        if changed_tests.intersection(document["verification"]["tests"])
    }
    seeds = changed | source_assets | evidence_assets
    if runtime_requirements_changed:
        seeds.update(current)
    removed = previous.keys() - current.keys()
    return {
        "schema": SCHEMA,
        "mode": "snapshot_comparison",
        "candidate_commit": candidate["git_commit"],
        "candidate_manifest_digest": candidate_manifest_digest,
        "comparison_commit": baseline["git_commit"],
        "comparison_manifest_digest": comparison_manifest_digest,
        "baseline_approval_verified": False,
        "runtime_requirements_changed": runtime_requirements_changed,
        "review_asset_ids": sorted(_reverse_dependents(seeds | removed, current) & current.keys()),
        "changed_document_ids": sorted(changed),
        "mechanical_only_document_ids": sorted(mechanical),
        "removed_asset_ids": sorted(removed),
        "changed_paths": changed_paths,
        "unresolved_source_paths": unresolved,
        "removed_assets_require_manual_review": bool(removed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_snapshot", type=Path)
    parser.add_argument("--comparison-snapshot", type=Path)
    args = parser.parse_args()
    try:
        result = review_scope(args.candidate_snapshot, args.comparison_snapshot)
    except (
        KeyError, OSError, ValueError, subprocess.CalledProcessError,
        json.JSONDecodeError, zipfile.BadZipFile,
    ) as error:
        print(f"review scope failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
