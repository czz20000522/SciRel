"""The migration worksheet must show the limits, not only the claims.

A worksheet that lists only sentences matching a basis phrase would invite the reader
to write `basis` and drop the qualifier next to it -- "independent references cover
only these six input tuples" would become "has an independent reference". That is the
overclaim this whole field exists to prevent, so the limits section is tested.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import propose_evidence_basis as worksheet  # noqa: E402


def _root(tmp_path: Path, entries: list[str]) -> Path:
    (tmp_path / "tools" / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / worksheet.BASELINE).write_text(
        json.dumps({"entries": [{"asset_id": a, "reason": "pending"} for a in entries]}),
        encoding="utf-8",
    )
    (tmp_path / worksheet.CATALOG).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _contract(
    root: Path, asset: str, scope: list[str], limitations: list[str], ceiling: str
) -> None:
    (root / worksheet.CATALOG / f"{asset}.json").write_text(
        json.dumps(
            {
                "asset_id": asset,
                "verification": {
                    "scope": scope,
                    "known_limitations": limitations,
                    "evidence_ceiling": ceiling,
                    "tests": ["tests/x/test_y.py"],
                },
            }
        ),
        encoding="utf-8",
    )


def test_a_qualified_claim_also_shows_its_limit(tmp_path):
    root = _root(tmp_path, ["scirel.x.qualified"])
    _contract(
        root,
        "scirel.x.qualified",
        ["Independent references cover only these six input tuples."],
        ["This does not establish a physical electron equilibrium."],
        "Bounded.",
    )
    record = worksheet.worksheet("scirel.x.qualified", root)
    assert any("only these six input tuples" in c for c in record["claims"])
    assert any("does not establish" in limit for limit in record["limits"]), record["limits"]


def test_the_tool_writes_nothing(tmp_path):
    root = _root(tmp_path, ["scirel.x.noop"])
    _contract(root, "scirel.x.noop", ["Independent reference."], [], "Bounded.")
    before = (root / worksheet.CATALOG / "scirel.x.noop.json").read_text(encoding="utf-8")
    assert worksheet.main(["--asset", "scirel.x.noop", "--root", str(root)]) == 0
    assert (root / worksheet.CATALOG / "scirel.x.noop.json").read_text(encoding="utf-8") == before


def test_an_unknown_asset_is_unobserved(tmp_path):
    root = _root(tmp_path, [])
    assert worksheet.main(["--asset", "scirel.x.missing", "--root", str(root)]) == 2


def test_the_repository_worksheet_runs():
    """The pending list comes from the real baseline, so this catches a broken one."""
    assert worksheet.main(["--limit", "1"]) == 0
