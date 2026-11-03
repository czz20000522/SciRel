"""Solved example reports pass the validator, and the validator rejects weak reports."""

import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/development/usage/scirel-solving/scripts"))
import validate_report  # noqa: E402


@pytest.mark.parametrize(
    "report", sorted(ROOT.glob("examples/*/REPORT.md")), ids=lambda p: p.parent.name
)
def test_example_reports_pass_the_validator(report):
    assert validate_report.validate(report) == []


GOOD = """# t

## 答案
影响约 3%。

## 问题与理解
理解。

## 物理模型与方法
用 $B=\\mu_0 I$。

## 结果
![图](f.png)

*图 1　说明。*

## 讨论
讨论。

## 结论
结论。

## 附录
x 0.123457
"""


def _report(tmp_path, text):
    (tmp_path / "f.png").write_bytes(b"png")
    path = tmp_path / "REPORT.md"
    path.write_text(text, encoding="utf-8")
    return validate_report.validate(path)


def test_validator_accepts_a_minimal_report(tmp_path):
    assert _report(tmp_path, GOOD) == []


@pytest.mark.parametrize(
    "change, message",
    [
        (("## 答案\n影响约 3%。\n\n", ""), "missing section"),
        (("## 讨论", "## 结论2\n\n## 讨论"), None),
        (("影响约 3%", "影响约 1.2345%"), "significant digits"),
        (("影响约 3%", "影响约 1.234%"), None),
        (("x 0.123457", "x 0.1234567"), "digits for the appendix"),
        (("用 $B=\\mu_0 I$。", "先做转置。"), "implementation detail"),
        (("用 $B=\\mu_0 I$。", "只有文字。"), "no formula"),
        (("![图](f.png)\n\n*图 1　说明。*", "无图"), "no figure"),
        (("*图 1　说明。*", "说明"), "no caption"),
        (("f.png", "missing.png"), "missing figure"),
        (("用 $B=\\mu_0 I$。", "用 $B$。\n\n```\ncode\n```"), "code blocks"),
    ],
)
def test_validator_rejects_weak_reports(tmp_path, change, message):
    errors = _report(tmp_path, GOOD.replace(*change))
    if message is None:
        assert errors == []
    else:
        assert any(message in error for error in errors), errors


def test_validator_accepts_declared_absence_with_a_reason_only(tmp_path):
    text = GOOD.replace("![图](f.png)\n\n*图 1　说明。*", "无图")
    assert _report(tmp_path, text + "<!-- report: figures=none; reason=概念问题 -->\n") == []
    assert _report(tmp_path, text + "<!-- report: figures=none; reason= -->\n") != []


def test_validator_requires_failed_checks_to_be_reported(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/checks.json").write_text(
        json.dumps([{"name": "symmetry_check", "status": "FAIL"}])
    )
    assert any("symmetry_check" in error for error in _report(tmp_path, GOOD))
    assert _report(tmp_path, GOOD + "symmetry_check 未通过。\n") == []


def test_validator_keeps_long_tables_out_of_the_body(tmp_path):
    rows = "| a |\n| --- |\n" + "".join(f"| {i} |\n" for i in range(12))
    assert any("table too long" in e for e in _report(tmp_path, GOOD.replace("讨论。", rows)))


def test_framework_ships_with_the_solving_skill_and_needs_nothing_from_the_repository():
    sys.path.insert(0, str(ROOT / "scripts"))
    import solving_skill

    skill = ROOT / "skills/development/usage/scirel-solving"
    closure = solving_skill.load_solving_skill(skill)
    for name in (
        "references/workflow.md",
        "references/method-design.md",
        "references/report-format.md",
        "references/example-report.md",
        "scripts/validate_report.py",
    ):
        assert name in closure, name
    for name, data in closure.items():
        if name.endswith(".md"):
            assert not re.search(rb"(?<!catalog/)examples/", data), name
            assert b"skills/development/usage" not in data, name


def test_gap_response_offers_the_closest_terms_and_a_way_forward():
    sys.path.insert(0, str(ROOT / "scripts"))
    from capability_query import query_capabilities
    from scirel_docs import build_capability_index

    documents = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "catalog/examples").glob("*.json"))
    ]
    result = query_capabilities(
        build_capability_index(documents, source_revision="0" * 40),
        {"schema": "scirel.capability-query", "q": "circular coil nonexistentword"},
    )
    assert result["status"] == "gap"
    assert result["gap"]["retry_hint"]
    assert result["gap"]["closest_terms"]
    assert all(item["matched_terms"] for item in result["gap"]["closest_terms"])


def test_delivered_skills_speak_to_any_user_and_stay_free_of_internal_content():
    # Words that belong to maintainers and evaluation, not to a user's agent.
    internal = re.compile(
        r"RULES\.md|AGENTS\.md|ARCHITECTURE\.md|benchmark|hidden oracle|gap card|缺口卡|intake|ATTEMPTED"
        r"|RUNTIME_GAP|internal run|external run|batch entry",
        re.I,
    )
    # A hand-written catalog size would go stale as the catalog grows.
    catalog_size = re.compile(
        r"\b\d{2,4} (public |admitted )?(contracts|assets|capabilities)\b|\d{2,4} ?(份|个)合同"
    )
    hits = []
    for name in ("scirel-solving", "scirel-capability-discovery", "scirel-result-validation"):
        for path in (ROOT / "skills/development/usage" / name).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            hits += [
                f"{path.name}: {m.group(0)}"
                for pattern in (internal, catalog_size)
                for m in pattern.finditer(text)
            ]
    assert hits == []


def test_wheel_metadata_readme_does_not_link_to_solved_examples():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert not re.search(r"(?<!catalog/)examples/", readme) and "REPORT.md" not in readme
