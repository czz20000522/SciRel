#!/usr/bin/env python3
"""Check the structure of a task report. Physics still needs a human reader.

Usage: python validate_report.py REPORT.md   (prints errors; exit status 1 on any)
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

SECTIONS = (
    ("答案", "Answer"),
    ("问题与理解", "Problem and understanding"),
    ("物理模型与方法", "Physical model and method"),
    ("结果", "Results"),
    ("讨论", "Discussion"),
    ("结论", "Conclusion"),
    ("附录", "Appendix"),
)
MAX_BODY_TABLE_ROWS = 10
MAX_BODY_SIGNIFICANT_DIGITS = 4
MAX_APPENDIX_SIGNIFICANT_DIGITS = 6
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
FENCE = re.compile(r"^```.*?^```[ \t]*$", re.M | re.S)
MATH = re.compile(r"\$[^$\n]+\$|\$\$")
NUMBER = re.compile(r"(?<![\w.])[-+]?(\d+\.\d+|\.\d+)(?:[eE][-+]?\d+)?(?![\w.])|(?<![\w.])[-+]?\d+[eE][-+]?\d+(?![\w.])")
IMPLEMENTATION_TERMS = re.compile(r"轴序|转置|数组形状|数据流|dtype|ndarray|array shape|axis order|\.py\b", re.I)
DECLARATION = "<!-- report: {}=none; reason="


def split_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^## +(.+?)[ \t]*$", FENCE.sub("", text), flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def _declared(text: str, name: str) -> bool:
    start = text.find(DECLARATION.format(name))
    if start < 0:
        return False
    reason = text[start + len(DECLARATION.format(name)):text.find("-->", start)]
    return bool(reason.strip())


def _significant_digits(token: str) -> int:
    mantissa = re.split(r"[eE]", token.lstrip("+-"))[0].replace(".", "").lstrip("0")
    return len(mantissa)


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    sections = split_sections(text)
    names = [name for name, _ in sections]
    expected = [next((option for option in pair if option in names), pair[0]) for pair in SECTIONS]
    errors = [f"missing section: {name}" for name in expected if name not in names]
    if errors:
        return errors
    if [name for name in names if name in expected] != expected:
        errors.append(f"sections out of order; expected {expected}")
    by_name = dict(sections)
    answer, method, results, appendix_name = (by_name[expected[i]] for i in (0, 2, 3, 6))
    if not answer.strip():
        errors.append("the answer section is empty")
    raw_method = re.search(r"^## +" + re.escape(expected[2]) + r".*?(?=^## )", text, re.M | re.S)
    if raw_method and "```" in raw_method.group(0):
        errors.append("the method section must not contain code blocks")
    if hit := IMPLEMENTATION_TERMS.search(method):
        errors.append(f"the method section contains an implementation detail: {hit.group(0)!r}")
    if not MATH.search(method) and not _declared(text, "math"):
        errors.append("the method section has no formula; add one or declare math=none with a reason")

    images = IMAGE.findall(results)
    if not images and not _declared(text, "figures"):
        errors.append("the results section has no figure; add one or declare figures=none with a reason")
    for target in IMAGE.findall(text):
        if not (path.parent / target).is_file():
            errors.append(f"missing figure file: {target}")
    for match in IMAGE.finditer(results):
        following = results[match.end():].lstrip()
        if not following.startswith(("*图", "*Figure", "*Fig")):
            errors.append(f"figure has no caption: {match.group(1)}")
    for target in LINK.findall(text):
        if not re.match(r"[a-z]+:", target) and not (path.parent / target).exists():
            errors.append(f"broken link: {target}")

    for name, body in sections:
        if name == expected[6]:
            for match in NUMBER.finditer(body):
                if _significant_digits(match.group(0)) > MAX_APPENDIX_SIGNIFICANT_DIGITS:
                    errors.append(f"{name}: too many significant digits for the appendix: {match.group(0)}")
            continue
        rows = sum(1 for line in body.splitlines() if line.lstrip().startswith("|") and not set(line) <= set("|- :"))
        if rows - 1 > MAX_BODY_TABLE_ROWS:
            errors.append(f"{name}: table too long for the body ({rows - 1} rows); move it to the appendix")
        for match in NUMBER.finditer(body):
            if _significant_digits(match.group(0)) > MAX_BODY_SIGNIFICANT_DIGITS:
                errors.append(f"{name}: too many significant digits: {match.group(0)}")

    checks = path.parent / "data" / "checks.json"
    if checks.is_file():
        records = json.loads(checks.read_text(encoding="utf-8"))
        for record in records:
            if record.get("status") != "PASS" and record.get("name") not in text:
                errors.append(f"failed check is not reported: {record.get('name')}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    errors = validate(Path(argv[1]))
    for error in errors:
        print("ERROR:", error)
    if not errors:
        print("report structure: PASS (physics needs a human reader)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
