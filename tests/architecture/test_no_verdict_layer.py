"""RULES.md says the judgement layer must not come back "under another name".

The layer was deleted because it judged the implementation from records derived from
that same implementation -- the dependency ran backwards. The rule that replaced it is
prose: "Do not rebuild it under another name."

Prose is exactly what this rule cannot rely on. A helper that accumulates accepted
lists is easy to add and hard to notice, and its shape ("a table that says which
assets are approved") is the defect, not its filename. So this test pins the shapes
that were actually deleted.

**What it does not catch** (stated here because a guard read as complete is worse than
no guard): a judgement table that shares none of these names -- for example
``catalog/review/approved.json`` or a verdict column added to an existing file. Those
still need review. What is caught is the literal regression: someone restoring
``VERDICTS.json`` / ``HOLD.json`` / ``review_gate.py`` or cloning them under a name
containing "verdict" or "hold" inside ``catalog/review/``.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The files RULES.md names as deleted. Restoring any of them is the exact regression.
DELETED_PATHS = (
    "catalog/review/VERDICTS.json",
    "catalog/review/HOLD.json",
    "catalog/review/HUMAN_REVIEW_TODO.md",
    "catalog/review/MERGE_CHAIN.md",
    "scripts/review_gate.py",
    "scripts/review_harness.py",
)

# Same shape, different name: a per-file or per-record verdict/hold table.
SHAPE = re.compile(r"(verdict|hold)", re.I)


def shape_hits(root: Path) -> list[str]:
    """Files under catalog/review/ whose name repeats the deleted layer's shape."""
    review = root / "catalog" / "review"
    if not review.is_dir():
        return []
    hits = []
    for path in review.rglob("*"):
        if path.is_file() and SHAPE.search(path.stem):
            hits.append(path.relative_to(root).as_posix())
    return sorted(hits)


def script_hits(root: Path) -> list[str]:
    """Review-gate style scripts by name, wherever they are put."""
    scripts = root / "scripts"
    if not scripts.is_dir():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in scripts.glob("*.py")
        if SHAPE.search(path.stem) and "review" in path.stem.lower()
    )


def test_the_deleted_judgement_layer_is_still_gone():
    present = [path for path in DELETED_PATHS if (ROOT / path).exists()]
    assert not present, (
        "the deleted judgement layer is back: "
        + ", ".join(present)
        + "; it judged the implementation from records derived from it (see RULES.md 'No manual verdict tables')"
    )


def test_no_verdict_shaped_table_under_catalog_review():
    assert shape_hits(ROOT) == [], (
        "a verdict/hold shaped table reappeared under catalog/review: "
        + ", ".join(shape_hits(ROOT))
    )


def test_no_review_gate_script():
    assert script_hits(ROOT) == [], "a review-gate style script reappeared: " + ", ".join(
        script_hits(ROOT)
    )


def test_the_guard_would_catch_a_renamed_copy(tmp_path: Path):
    """The predicate must fire on the regression, not merely pass today."""
    (tmp_path / "catalog" / "review").mkdir(parents=True)
    (tmp_path / "catalog" / "review" / "approved-verdicts-2026.json").write_text(
        "{}", encoding="utf-8"
    )
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "review_hold_check.py").write_text("", encoding="utf-8")
    assert shape_hits(tmp_path) == ["catalog/review/approved-verdicts-2026.json"]
    assert script_hits(tmp_path) == ["scripts/review_hold_check.py"]


def test_the_guard_does_not_fire_on_prose_about_the_deleted_layer(tmp_path: Path):
    """Mentioning the layer in documentation is required; only files count."""
    docs = tmp_path / "docs" / "maintainer"
    docs.mkdir(parents=True)
    (docs / "observation-integrity.md").write_text("VERDICTS.json was deleted", encoding="utf-8")
    assert shape_hits(tmp_path) == []
    assert script_hits(tmp_path) == []
