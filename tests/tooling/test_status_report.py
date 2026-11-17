"""Keep the status snapshot's measured block from going stale.

The file was merged saying `revision 7f1eef8c` while `main` had already moved on, which is
worse than having no number at all: a reader trusts a stamp that is quietly wrong. Written
by hand, the block goes stale on the next batch; generated and gated, it cannot.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "status_report.py"
STATUS = ROOT / "docs" / "maintainer" / "status.md"


def _generated() -> str:
    done = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _committed_block() -> str:
    text = STATUS.read_text(encoding="utf-8")
    match = re.search(r"<!-- status-report:begin -->.*?<!-- status-report:end -->", text, re.S)
    assert match, "status.md lost its generated block markers"
    return match.group(0).strip()


def test_the_committed_block_matches_a_fresh_generation():
    """A batch that changes a count must regenerate the block, not edit it by hand."""
    committed = _committed_block()
    fresh = _generated()
    if committed != fresh:
        stale = [line for line in committed.splitlines() if line not in fresh.splitlines()]
        raise AssertionError(
            "docs/maintainer/status.md 的测量块与现场生成结果不一致；"
            "运行 `python3 scripts/status_report.py --write` 重新生成。\n"
            "提交块里多出或过期的行：\n  " + "\n  ".join(stale[:12])
        )


def test_the_block_carries_no_commit_id():
    """A generated block must be invariant under commits that do not change the numbers.

    An earlier version embedded HEAD, which made the block stale on every commit and the
    gate impossible to satisfy. The numbers are versioned by the commit that generated them.
    """
    block = _committed_block()
    assert not re.search(r"\b[0-9a-f]{40}\b", block), block
    assert "revision" not in block.lower(), block


def test_every_measured_row_names_its_recompute_recipe():
    """A number without a recipe cannot be checked by the next reader."""
    block = _committed_block()
    headers = {"项", "值", "量", "复算口径（在仓库根执行）", "证据覆盖", "份数"}
    measured = []
    for line in block.splitlines():
        if not line.startswith("| ") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0] in headers:  # 表头行
            continue
        measured.append(line)
    assert measured, "the block has no measured rows"

    # 三列表格每行自带口径；两列表格（revision、证据覆盖）共用表下那句"口径："。
    shared_recipe = any(line.startswith("口径：") for line in block.splitlines())
    for row in measured:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) == 2:
            assert shared_recipe, f"two-column row without a shared recipe: {row}"
            continue
        assert len(cells) >= 3, row
        assert cells[-1].strip("` "), f"row has no recipe: {row}"
