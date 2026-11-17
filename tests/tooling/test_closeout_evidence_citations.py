"""Keep the closeout evidence page's citations pointing at files that exist.

The page quotes command output. Quoted output goes stale, and one failure mode is
worse than a stale number: **the number stays right and the citation goes wrong**.
That happened here -- a floor of 9541 was attributed to an anchor that a later
anchor had superseded, so a reader checking the named file would find a revision
that no longer produced the number.

This test does not pin numbers (they drift by design and the page says so). It pins
the property that a named anchor is a real file, and that the anchor currently
setting the release floor is named somewhere in the page -- so an upgrade lands as
a diff to the page, not as a silent mismatch.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "maintainer" / "closeout-evidence.md"
ANCHORS = ROOT / "skills" / "development" / "scirel-acceptance" / "anchors"

sys.path.insert(0, str(ROOT / "skills" / "development" / "scirel-acceptance" / "scripts"))

NAMED = re.compile(r"release-[0-9a-f]{12}")


def test_every_anchor_named_in_the_page_exists():
    text = PAGE.read_text(encoding="utf-8")
    named = set(NAMED.findall(text))
    assert named, "the page names no anchor; the floor section lost its citation"
    missing = sorted(name for name in named if not (ANCHORS / f"{name}.json").is_file())
    assert missing == [], f"the page cites anchors that do not exist: {missing}"


def test_the_anchor_that_sets_the_release_floor_is_named_in_the_page():
    """An upgraded floor must show up in the page, not just in the anchors directory."""
    from check_all import selection_floor

    floor = selection_floor("release")
    if floor is None:
        return  # no release anchor yet; nothing to cite
    stem = Path(floor.anchor).stem
    assert stem in PAGE.read_text(encoding="utf-8"), (
        f"the release floor now comes from {stem}, but the evidence page does not name it; "
        "a reader checking the page's citation would land on the superseded anchor"
    )
