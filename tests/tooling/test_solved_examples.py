"""Solved examples stay reproducible, and the report validator rejects weak reports."""

import importlib.util
import json
from pathlib import Path
import re
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "examples" / "coil-offset"
sys.path.insert(0, str(ROOT / "skills/development/usage/scirel-solving/scripts"))
import validate_report  # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def solve():
    return _load(CASE / "solve.py", "coil_offset_solve")


@pytest.mark.parametrize(
    "report", sorted(ROOT.glob("examples/*/REPORT.md")), ids=lambda p: p.parent.name
)
def test_example_reports_pass_the_validator(report):
    assert validate_report.validate(report) == []


def test_coil_report_is_regenerated_exactly_from_saved_results():
    make_report = _load(CASE / "make_report.py", "coil_offset_report")
    assert make_report.render() == (CASE / "REPORT.md").read_text(encoding="utf-8")


def test_coil_saved_summary_matches_a_fresh_calculation(solve):
    saved = json.loads((CASE / "data/summary.json").read_text(encoding="utf-8"))["states"]
    for name, rings in solve.STATES.items():
        fresh = solve.metrics(rings)
        assert fresh["U"] == pytest.approx(saved[name]["U"], rel=1e-12)
        assert fresh["bref_T"] == pytest.approx(saved[name]["bref_T"], rel=1e-12)


def test_coil_all_saved_checks_pass_and_are_recomputed(solve):
    states = {name: solve.metrics(rings) for name, rings in solve.STATES.items()}
    fresh = solve.run_checks(states)
    assert [c["name"] for c in fresh if c["status"] != "PASS"] == []
    saved = json.loads((CASE / "data/checks.json").read_text(encoding="utf-8"))
    assert {c["name"]: c["status"] for c in saved} == {c["name"]: c["status"] for c in fresh}


def test_coil_centre_is_the_helmholtz_value_and_doubling_current_doubles_the_field(solve):
    rings = solve.STATES["nominal"]
    single = solve.field(rings, [[0.0, 0.0]])["Bz"][0]
    assert single == pytest.approx(
        (4 / 5) ** 1.5 * solve.MU0 * solve.CURRENT / solve.RADIUS, rel=1e-12
    )
    assert solve.field(rings, [[0.0, 0.0]], current=2 * solve.CURRENT)["Bz"][0] == pytest.approx(
        2 * single
    )


def test_coil_reversing_the_current_reverses_the_field_and_keeps_the_tilt(solve):
    points = solve.grid_points()
    forward = solve.field(solve.STATES["offset"], points)
    backward = solve.field(solve.STATES["offset"], points, current=-solve.CURRENT)
    np.testing.assert_allclose(backward["Bz"], -forward["Bz"])
    np.testing.assert_allclose(
        np.abs(np.arctan2(backward["Br"], backward["Bz"]) % np.pi - np.pi / 2),
        np.abs(np.arctan2(forward["Br"], forward["Bz"]) % np.pi - np.pi / 2),
    )


def test_coil_independent_reference_detects_a_wrong_factor_or_sign(solve):
    points = solve.grid_points()
    reference = solve.biot_savart(solve.STATES["nominal"], points, nodes=256)
    kernel = solve.field(solve.STATES["nominal"], points)
    tolerance = 1e-11 * solve.MU0 * solve.CURRENT / (2 * solve.RADIUS)
    assert np.max(np.abs(kernel["Bz"] - reference["Bz"])) <= tolerance
    assert np.max(np.abs(2 * kernel["Bz"] - reference["Bz"])) > tolerance
    assert np.max(np.abs(-kernel["Br"] - reference["Br"])) > tolerance


def test_coil_uniformity_uses_only_the_nine_central_points(solve):
    points = solve.grid_points()
    assert sum(solve.is_center(point) for point in points) == 9
    state = solve.metrics(solve.STATES["nominal"])
    assert state["center_points"] == 9
    for r, z in state["U_at"]:
        assert r <= 0.10 and abs(z) <= 0.10


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
x 0.123456789
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
        (("影响约 3%", "影响约 1.2345678%"), "significant digits"),
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
            assert b"examples/coil-offset" not in data, name
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


def test_delivered_skills_do_not_contain_answers_from_the_reference_demo():
    summary = json.loads((CASE / "data/summary.json").read_text(encoding="utf-8"))
    nominal, offset = summary["states"]["nominal"], summary["states"]["offset"]
    values = [
        100 * nominal["U"],
        100 * offset["U"],
        1e3 * nominal["bref_T"],
        1e3 * offset["bref_T"],
        1e3 * nominal["tilt_max_rad"],
        1e3 * offset["tilt_max_rad"],
    ]
    needles = {f"{value:.2f}" for value in values} | {
        f"{nominal['bref_T']:.8f}",
        f"{offset['bref_T']:.8f}",
    }
    hits = []
    for path in (ROOT / "skills/development/usage").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        hits += [f"{path.name}: {needle}" for needle in needles if needle in text]
    assert hits == []


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
    assert "examples/coil-offset" not in readme and "REPORT.md" not in readme
