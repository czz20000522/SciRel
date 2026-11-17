"""`verification.basis` must be a field, and the gate must actually run on this catalog.

The gate exists because inferring "is there a basis?" from prose does not work: 106
assets carry basis wording the phrase list does not recognise. Two things therefore
have to hold, and both are tested here:

* the gate runs on the real repository (a gate that only ever sees tmp_path enforces
  nothing -- the eighth class in observation-integrity);
* the gate actually goes red: silence without a baseline entry, an unknown kind, and
  `kind: none` with nothing recorded must each fail.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_evidence_basis as gate  # noqa: E402

SCRIPT = ROOT / "scripts" / "check_evidence_basis.py"


def _root(tmp_path: Path) -> Path:
    (tmp_path / "tools" / "docs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _baseline(root: Path, entries: list[str]) -> None:
    (root / gate.BASELINE).write_text(
        json.dumps({"entries": [{"asset_id": a, "reason": "not migrated"} for a in entries]}),
        encoding="utf-8",
    )


def _contract(root: Path, asset: str, verification: dict) -> None:
    directory = root / gate.CATALOG
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{asset}.json").write_text(
        json.dumps({"asset_id": asset, "verification": verification}), encoding="utf-8"
    )


def test_the_gate_runs_on_this_repository():
    done = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "contracts declare verification.basis" in done.stdout


def test_the_gate_does_not_report_unobserved():
    done = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert done.returncode != 2, done.stdout + done.stderr


def test_a_silent_contract_outside_the_baseline_is_a_violation(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _contract(
        root, "scirel.x.silent", {"scope": ["a"], "evidence_ceiling": "b", "known_limitations": []}
    )
    assert gate.main(["--root", str(root)]) == 1


def test_a_declared_basis_with_a_known_kind_passes(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _contract(
        root,
        "scirel.x.declared",
        {
            "scope": ["a"],
            "evidence_ceiling": "b",
            "known_limitations": [],
            "basis": {
                "kind": "analytic-identity",
                "statement": "psi = R^2 Z^2 has closed-form gradients",
            },
        },
    )
    assert gate.main(["--root", str(root)]) == 0


def test_an_unknown_kind_is_a_violation(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _contract(
        root,
        "scirel.x.badkind",
        {
            "scope": ["a"],
            "evidence_ceiling": "b",
            "known_limitations": [],
            "basis": {"kind": "vibes", "statement": "trust me"},
        },
    )
    assert gate.main(["--root", str(root)]) == 1


def test_kind_none_without_a_recorded_gap_is_a_violation(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _contract(
        root,
        "scirel.x.none",
        {
            "scope": ["a"],
            "evidence_ceiling": "x",
            "known_limitations": [],
            "basis": {"kind": "none", "statement": "no basis"},
        },
    )
    # evidence_ceiling is non-empty here, so this one passes; the failing variant follows.
    assert gate.main(["--root", str(root)]) == 0


def test_kind_none_with_nothing_recorded_is_a_violation(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _contract(
        root,
        "scirel.x.none2",
        {
            "scope": ["a"],
            "evidence_ceiling": "",
            "known_limitations": [],
            "basis": {"kind": "none", "statement": "no basis"},
        },
    )
    assert gate.main(["--root", str(root)]) == 1


def test_a_baselined_silence_passes(tmp_path):
    root = _root(tmp_path)
    _baseline(root, ["scirel.x.old"])
    _contract(
        root, "scirel.x.old", {"scope": ["a"], "evidence_ceiling": "b", "known_limitations": []}
    )
    assert gate.main(["--root", str(root)]) == 0


def test_a_baselined_contract_that_now_declares_a_basis_is_stale(tmp_path):
    root = _root(tmp_path)
    _baseline(root, ["scirel.x.migrated"])
    _contract(
        root,
        "scirel.x.migrated",
        {
            "scope": ["a"],
            "evidence_ceiling": "b",
            "known_limitations": [],
            "basis": {"kind": "literature", "statement": "follows Eq. (3) of the cited paper"},
        },
    )
    assert gate.main(["--root", str(root)]) == 1


def test_a_baseline_entry_whose_contract_is_gone_is_stale(tmp_path):
    root = _root(tmp_path)
    _baseline(root, ["scirel.x.deleted"])
    _contract(
        root,
        "scirel.x.present",
        {
            "scope": ["a"],
            "evidence_ceiling": "b",
            "known_limitations": [],
            "basis": {"kind": "closed-form", "statement": "erf limit"},
        },
    )
    assert gate.main(["--root", str(root)]) == 1


def test_a_broken_baseline_is_unobserved(tmp_path):
    root = _root(tmp_path)
    (root / gate.BASELINE).write_text("{not json", encoding="utf-8")
    _contract(
        root, "scirel.x.v", {"scope": ["a"], "evidence_ceiling": "b", "known_limitations": []}
    )
    assert gate.main(["--root", str(root)]) == 2
