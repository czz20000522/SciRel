"""The output-channel check must fail, not warn, when a contract stays silent.

The point of this gate is that 92 contracts are baselined. If the checker were
permissive or the baseline were a blanket allow-list, those 92 would never be
paid down and no new silent contract would be caught. These tests pin the three
things that make it a ratchet rather than a rubber stamp:

* silence is a violation;
* a baselined silence still passes (that is the ratchet's current state);
* a baseline entry that no longer violates is an error, so the fix and the
  deletion land in one commit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_output_channel_declaration as check  # noqa: E402


def _contract(asset: str, outputs: list[dict], **extra) -> dict:
    document = {"asset_id": asset, "outputs": outputs, "identity": extra.pop("identity", {})}
    document.update(extra)
    return document


def _write(root: Path, document: dict) -> None:
    directory = root / check.CATALOG
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{document['asset_id']}.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8"
    )


def _baseline(root: Path, assets: list[str]) -> None:
    path = root / check.BASELINE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"entries": [{"asset_id": a, "reason": "measured, not yet paid down"} for a in assets]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _root(tmp_path: Path) -> Path:
    (tmp_path / "tools" / "docs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_a_silent_single_output_contract_is_a_violation(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _write(root, _contract("scirel.x.silent", [{"name": "value", "dtype": "float64 array"}]))
    assert check.main(["--root", str(root)]) == 1


def test_a_contract_that_states_positional_returning_passes(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _write(
        root,
        _contract(
            "scirel.x.positional",
            [
                {
                    "name": "value",
                    "dtype": "float64 array",
                    "description": "Returned directly as the callable's single positional value.",
                }
            ],
        ),
    )
    assert check.main(["--root", str(root)]) == 0


def test_a_result_mapping_field_passes(tmp_path):
    root = _root(tmp_path)
    _baseline(root, [])
    _write(
        root,
        _contract(
            "scirel.x.mapping",
            [{"name": "W_el", "description": "Field ``W_el`` of the returned ``Result`` mapping."}],
        ),
    )
    assert check.main(["--root", str(root)]) == 0


def test_a_multi_output_contract_is_not_checked_here(tmp_path):
    """Two or more outputs must return a Result; that is a different criterion."""
    root = _root(tmp_path)
    _baseline(root, [])
    _write(root, _contract("scirel.x.multi", [{"name": "a"}, {"name": "b"}]))
    assert check.main(["--root", str(root)]) == 0


def test_a_baselined_silence_passes(tmp_path):
    root = _root(tmp_path)
    _baseline(root, ["scirel.x.known"])
    _write(root, _contract("scirel.x.known", [{"name": "value", "dtype": "float64 array"}]))
    assert check.main(["--root", str(root)]) == 0


def test_a_baselined_contract_that_now_states_its_channel_is_stale(tmp_path):
    """Fixing the contract without deleting the entry must fail (the fix is the diff)."""
    root = _root(tmp_path)
    _baseline(root, ["scirel.x.fixed"])
    _write(
        root,
        _contract(
            "scirel.x.fixed",
            [{"name": "value", "description": "Returned positionally as one float64 array."}],
        ),
    )
    assert check.main(["--root", str(root)]) == 1


def test_a_baseline_entry_whose_contract_is_gone_is_stale(tmp_path):
    root = _root(tmp_path)
    _baseline(root, ["scirel.x.deleted"])
    _write(
        root,
        _contract("scirel.x.other", [{"name": "v", "description": "Returned positionally."}]),
    )
    assert check.main(["--root", str(root)]) == 1


def test_a_broken_baseline_is_unobserved_not_a_pass(tmp_path):
    root = _root(tmp_path)
    path = root / check.BASELINE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    _write(root, _contract("scirel.x.v", [{"name": "v"}]))
    # 未观测是退出码 2，不是异常、也不是通过
    assert check.main(["--root", str(root)]) == 2


def test_a_baseline_entry_without_a_reason_is_refused(tmp_path):
    root = _root(tmp_path)
    path = root / check.BASELINE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"entries": [{"asset_id": "scirel.x.v"}]}), encoding="utf-8")
    _write(root, _contract("scirel.x.v", [{"name": "v"}]))
    # 未观测是退出码 2，不是异常、也不是通过
    assert check.main(["--root", str(root)]) == 2
