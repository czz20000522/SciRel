from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from requalify_document_selection import requalify_selection  # noqa: E402


SELECTION = ROOT / "provenance/selections/scientific-core-documents-20261015-r9.json"
BASELINE = "895bc40"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dev8_selection_reports_changed_plotting_contracts_without_editing() -> None:
    before = {
        path: path.read_bytes()
        for path in (ROOT / "catalog/examples").glob("*.json")
    }
    result = requalify_selection(
        selection_path=SELECTION,
        baseline_ref=BASELINE,
        old_version="0.1.0.dev8",
        new_version="0.1.0.dev9",
        require_complete=False,
    )

    assert result["selected_count"] == 260
    assert result["eligible_count"] == 257
    assert result["blocked_count"] == 3
    assert {
        item["asset_id"] for item in result["blocked"]
    } == {
        "scirel.plotting.mirror-patches",
        "scirel.plotting.scale-patches",
        "scirel.plotting.transpose-patches",
    }
    assert result["changed_paths"] == []
    assert before == {
        path: path.read_bytes()
        for path in (ROOT / "catalog/examples").glob("*.json")
    }


def test_complete_requalification_fails_closed_on_changed_contracts() -> None:
    with pytest.raises(ValueError, match="complete requalification is blocked"):
        requalify_selection(
            selection_path=SELECTION,
            baseline_ref=BASELINE,
            old_version="0.1.0.dev8",
            new_version="0.1.0.dev9",
        )


def test_apply_never_shrinks_a_blocked_selection(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--apply requires complete requalification"):
        requalify_selection(
            selection_path=SELECTION,
            baseline_ref=BASELINE,
            old_version="0.1.0.dev8",
            new_version="0.1.0.dev9",
            output_selection=tmp_path / "selection.json",
            apply=True,
            require_complete=False,
        )
    assert not (tmp_path / "selection.json").exists()


def test_explicit_proof_requalifies_a_changed_public_module(tmp_path: Path) -> None:
    module = ROOT / "src/scirel/geometry/plotting.py"
    test_paths = [
        ROOT / "tests/test_lazy_namespace.py",
        ROOT / "tests/pleiades/equilibrium/test_analysis_families.py",
    ]
    receipt = ROOT / "provenance/validation/scirel-dev9-linux-acceptance-20261017.json"
    manifest = {
        "schema": "scirel.document-requalification-proof.v1",
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "baseline_revision": subprocess.check_output(
            ["git", "rev-parse", f"{BASELINE}^{{commit}}"], cwd=ROOT, text=True
        ).strip(),
        "proofs": [
            {
                "asset_ids": [
                    "scirel.plotting.mirror-patches",
                    "scirel.plotting.scale-patches",
                    "scirel.plotting.transpose-patches",
                ],
                "module": "src/scirel/geometry/plotting.py",
                "module_sha256": _sha256(module),
                "test_paths": [
                    {"path": str(path.relative_to(ROOT)), "sha256": _sha256(path)}
                    for path in test_paths
                ],
                "receipt_paths": [
                    {"path": str(receipt.relative_to(ROOT)), "sha256": _sha256(receipt)}
                ],
            }
        ],
    }
    manifest_path = tmp_path / "plotting-proof.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = requalify_selection(
        selection_path=SELECTION,
        baseline_ref=BASELINE,
        old_version="0.1.0.dev8",
        new_version="0.1.0.dev9",
        proof_manifest=manifest_path,
    )

    assert result["selected_count"] == 260
    assert result["eligible_count"] == 260
    assert result["blocked_count"] == 0
    assert {
        item["asset_id"] for item in result["eligible"]
    } >= {
        "scirel.plotting.mirror-patches",
        "scirel.plotting.scale-patches",
        "scirel.plotting.transpose-patches",
    }
    assert result["proof_manifest_sha256"] == _sha256(manifest_path)


def test_explicit_proof_rejects_a_stale_module_digest(tmp_path: Path) -> None:
    module = ROOT / "src/scirel/geometry/plotting.py"
    receipt = ROOT / "provenance/validation/scirel-dev9-linux-acceptance-20261017.json"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    baseline = subprocess.check_output(
        ["git", "rev-parse", f"{BASELINE}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    manifest = {
        "schema": "scirel.document-requalification-proof.v1",
        "source_revision": head,
        "baseline_revision": baseline,
        "proofs": [
            {
                "asset_ids": ["scirel.plotting.mirror-patches"],
                "module": "src/scirel/geometry/plotting.py",
                "module_sha256": "0" * 64,
                "test_paths": [
                    {
                        "path": "tests/test_lazy_namespace.py",
                        "sha256": _sha256(ROOT / "tests/test_lazy_namespace.py"),
                    }
                ],
                "receipt_paths": [
                    {
                        "path": str(receipt.relative_to(ROOT)),
                        "sha256": _sha256(receipt),
                    }
                ],
            }
        ],
    }
    manifest_path = tmp_path / "stale-proof.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="module digest differs"):
        requalify_selection(
            selection_path=SELECTION,
            baseline_ref=BASELINE,
            old_version="0.1.0.dev8",
            new_version="0.1.0.dev9",
            proof_manifest=manifest_path,
        )
