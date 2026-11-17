"""Regenerate the measured block of the status snapshot.

Why this exists
---------------
``docs/maintainer/status.md`` records numbers that are true for one revision. Written by
hand they go stale the moment the next batch lands: the file was merged saying
``revision 7f1eef8c`` while ``main`` had already moved on, and a reader who trusts a stale
stamp is worse off than one who finds no number at all.

So the numbers are generated, not typed. The file keeps its prose, and everything between
the two markers is replaced wholesale by this script:

    python3 scripts/status_report.py --write     # refresh the block in place
    python3 scripts/status_report.py             # print it, change nothing

``tests/tooling/test_status_report.py`` fails when the committed block differs from a fresh
generation, so a batch that changes a count either regenerates the block or explains why the
number is deliberately frozen. That turns "remember to update the docs" into a gate.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "docs" / "maintainer" / "status.md"
BEGIN = "<!-- status-report:begin -->"
END = "<!-- status-report:end -->"


def _run(*args: str) -> str:
    done = subprocess.run(list(args), cwd=ROOT, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"{' '.join(args)} failed ({done.returncode}): {done.stderr!r}")
    return done.stdout


def _count_files(pattern: str, root: str) -> int:
    return len(list((ROOT / root).rglob(pattern)))


def _lines(root: str) -> int:
    return sum(
        len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        for path in (ROOT / root).rglob("*.py")
    )


def _public_functions() -> int:
    total = 0
    for path in (ROOT / "src" / "scirel").rglob("*.py"):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if re.match(r"def [a-zA-Z]", line):
                total += 1
    return total


def _domains() -> int:
    base = ROOT / "src" / "scirel"
    return sum(1 for path in base.iterdir() if path.is_dir() and (path / "__init__.py").is_file())


def _revision() -> str:
    return _run("git", "rev-parse", "--short", "HEAD").strip()


def _coverage() -> dict[str, int]:
    import json

    out = _run(sys.executable, "-B", "scripts/c1_evidence_coverage.py", "--format", "json")
    document = json.loads(out)
    return document.get("totals", document)


def build_block() -> str:
    totals = _coverage()
    rows = [
        (
            "合同（`catalog/examples/`）",
            len(list((ROOT / "catalog" / "examples").glob("scirel.*.json"))),
            "`ls catalog/examples/scirel.*.json | wc -l`",
        ),
        (
            "`src/scirel` 下 `.py` 文件",
            _count_files("*.py", "src/scirel"),
            "`find src/scirel -name '*.py' | wc -l`",
        ),
        (
            "`src/scirel` 行数",
            _lines("src/scirel"),
            "`find src/scirel -name '*.py' -exec cat {} + | wc -l`",
        ),
        (
            "模块级公开函数（`def` 顶格、非下划线开头）",
            _public_functions(),
            "`grep -rh '^def [a-zA-Z]' src/scirel --include='*.py' | wc -l`",
        ),
        (
            "顶层子包（含 `__init__.py`）",
            _domains(),
            "`ls -d src/scirel/*/ | wc -l` 后按 `__init__.py` 过滤",
        ),
        (
            "测试文件（`test_*.py`）",
            _count_files("test_*.py", "tests"),
            "`find tests -name 'test_*.py' | wc -l`",
        ),
    ]
    # 不放 HEAD：块一旦含当前提交号，任何提交都会让它立刻过期，永远无法满足。
    # 数字的定版方式是"生成它的那个提交"，用 `git log -1 -- docs/maintainer/status.md` 取。
    lines = [
        BEGIN,
        "| 量 | 值 | 复算口径（在仓库根执行） |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {name} | {value} | {recipe} |" for name, value, recipe in rows]
    lines.append("")
    lines.append(
        "口径：数字由本块上方的命令现场重算；本块不含提交号——"
        "引用时连同生成它的提交一起引用（`git log -1 -- docs/maintainer/status.md`）。"
    )
    if totals:
        lines += [
            "",
            "| 证据覆盖 | 份数 |",
            "| --- | --- |",
        ]
        for key in ("basis", "gap", "either", "neither", "total"):
            if key in totals:
                lines.append(f"| `{key}` | {totals[key]} |")
        lines.append("")
        lines.append(
            "口径：`python3 scripts/c1_evidence_coverage.py`；`neither` 是**合同文本缺口**，"
            "不是「没有证据」，也不是科学工作完成度。"
        )
    lines.append(END)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="replace the block in status.md")
    args = parser.parse_args(argv)

    block = build_block()
    if not args.write:
        print(block)
        return 0

    text = STATUS.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"status.md has no {BEGIN} … {END} block to replace")
    STATUS.write_text(pattern.sub(block, text, count=1), encoding="utf-8")
    print(f"status block regenerated in {STATUS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
