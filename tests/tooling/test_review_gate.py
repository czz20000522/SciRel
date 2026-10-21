"""Every catalog asset has an explicit admission verdict; exposure is gated."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import review_gate


def test_audit_verdict_gate_passes():
    assert review_gate.check() == []


def test_held_assets_are_not_exposed():
    hold = json.loads((ROOT / "catalog" / "review" / "HOLD.json").read_text())
    verdicts = json.loads((ROOT / "catalog" / "review" / "VERDICTS.json").read_text())
    for asset in hold["assets"]:
        assert verdicts["assets"][asset]["status"] == "human-review"
