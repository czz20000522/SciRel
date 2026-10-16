from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from requalify_document_selection import requalify_selection  # noqa: E402


SELECTION = ROOT / "provenance/selections/scientific-core-documents-20261015-r9.json"
BASELINE = "895bc40"


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
