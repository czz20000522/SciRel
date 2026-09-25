"""Suggest an expert review scope from exact frozen development snapshots.

This is a read-only change/impact report, not a scientific equivalence or approval gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

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


def _read_snapshot(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = json.loads(_snapshot_file(root, "manifest.json").read_text(encoding="utf-8"))
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
    return manifest, documents


def _scientific_document(document: dict[str, Any]) -> dict[str, Any]:
    comparable = {**document, "version": dict(document["version"])}
    comparable["version"].pop("implementation_version", None)
    return comparable


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=True
    )
    return result.stdout.decode("utf-8").strip()


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
    paths: list[str], candidate_commit: str, documents: dict[str, dict[str, Any]]
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
        if not callables or any(item not in by_callable for item in callables):
            unresolved.append(reason["changed_path"])
        else:
            affected.update(by_callable[item] for item in callables)
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
    candidate, current = _read_snapshot(candidate_dir)
    if baseline_dir is None:
        return {
            "schema": SCHEMA,
            "mode": "first_review",
            "candidate_commit": candidate["git_commit"],
            "comparison_commit": None,
            "baseline_approval_verified": False,
            "review_asset_ids": sorted(current),
            "changed_document_ids": sorted(current),
            "mechanical_only_document_ids": [],
            "removed_asset_ids": [],
            "changed_paths": [],
            "unresolved_source_paths": [],
            "removed_assets_require_manual_review": False,
        }

    baseline, previous = _read_snapshot(baseline_dir)
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
    source_assets, unresolved = _source_impact(source_paths, candidate["git_commit"], current)
    changed_tests = {path for path in changed_paths if path.startswith("tests/")}
    evidence_assets = {
        asset_id for asset_id, document in current.items()
        if changed_tests.intersection(document["verification"]["tests"])
    }
    seeds = changed | source_assets | evidence_assets
    removed = previous.keys() - current.keys()
    return {
        "schema": SCHEMA,
        "mode": "snapshot_comparison",
        "candidate_commit": candidate["git_commit"],
        "comparison_commit": baseline["git_commit"],
        "baseline_approval_verified": False,
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
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"review scope failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
