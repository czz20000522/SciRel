"""The objective report must not turn an unobservable criterion into a pass.

The report exists so the four completion criteria can be answered without
replaying a conversation. Its value depends on it staying three-state: a
criterion no tracked artifact can decide has to print ``not-observed`` even when
everything else is green.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import objective_status  # noqa: E402


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "tools" / "docs").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "skills/development/scirel-acceptance/scripts").mkdir(parents=True)
    (tmp_path / "catalog/examples").mkdir(parents=True)
    return tmp_path


def _inventory(root: Path, rules: list[dict]) -> None:
    (root / "tools/docs/rules-inventory.json").write_text(
        json.dumps({"schema": "scirel.rules-inventory.v1", "rules": rules}), encoding="utf-8"
    )


def _plan(root: Path, text: str) -> None:
    (root / "skills/development/scirel-acceptance/scripts/check_all.py").write_text(
        text, encoding="utf-8"
    )


def _basis_baseline(root: Path, entries: list[dict]) -> None:
    (root / "tools/docs/evidence-basis-baseline.json").write_text(
        json.dumps({"entries": entries}), encoding="utf-8"
    )


def _contract(root: Path, asset: str, verification: dict) -> None:
    (root / "catalog/examples" / f"{asset}.json").write_text(
        json.dumps({"asset_id": asset, "verification": verification}), encoding="utf-8"
    )


GOOD_RULE = {
    "id": "demo-1",
    "source": "AGENTS.md",
    "anchor": "demo",
    "state": "machine",
    "judged_by": ["scripts/demo_checker.py"],
    "judges": "everything.",
}
UNJUDGED_RULE = {
    "id": "demo-2",
    "source": "AGENTS.md",
    "anchor": "demo",
    "state": "unjudged",
    "why": "no decidable predicate exists for this rule at all.",
    "who": "the reviewer, against the checklist in the skill.",
}


def test_a_complete_tree_passes_the_three_decidable_criteria(tmp_path):
    root = _tree(tmp_path)
    _inventory(root, [GOOD_RULE, UNJUDGED_RULE])
    _plan(root, "scripts/demo_checker.py")
    _basis_baseline(root, [])
    _contract(root, "scirel.demo.asset", {"basis": {"kind": "closed-form", "statement": "x"}})
    assert [item["state"] for item in objective_status.report(root)] == [
        "pass",
        "pass",
        "pass",
        "not-observed",
    ]


def test_the_pr_criterion_is_never_reported_as_a_pass(tmp_path):
    """The receipt is not in the tree, so claiming pass would be a fabricated verdict."""
    root = _tree(tmp_path)
    _inventory(root, [])
    _plan(root, "")
    _basis_baseline(root, [])
    states = {item["criterion"]: item["state"] for item in objective_status.report(root)}
    assert states["each batch merged with an exclusive check"] == "not-observed"


def test_a_judge_the_plan_never_reaches_is_a_failure(tmp_path):
    root = _tree(tmp_path)
    _inventory(root, [GOOD_RULE])
    _plan(root, "something else")
    _basis_baseline(root, [])
    state, problems = objective_status.criterion_rules(root)
    assert state == "fail"
    assert "is not reached by the plan" in problems[0]


def test_a_judge_reached_through_a_test_counts_as_wired(tmp_path):
    root = _tree(tmp_path)
    _inventory(root, [GOOD_RULE])
    _plan(root, "")
    (root / "tests/test_demo.py").write_text("import demo_checker\n", encoding="utf-8")
    assert objective_status.criterion_rules(root)[0] == "pass"


def test_a_missing_field_for_the_state_is_a_failure(tmp_path):
    root = _tree(tmp_path)
    _inventory(
        root,
        [
            {
                "id": "demo-3",
                "state": "machine-partial",
                "judged_by": ["scripts/x.py"],
                "judges": "y",
            }
        ],
    )
    _plan(root, "scripts/x.py")
    state, problems = objective_status.criterion_rules(root)
    assert state == "fail"
    assert any("machine-partial needs does_not_judge" in problem for problem in problems)


def test_an_unjudged_rule_without_a_reason_is_a_failure(tmp_path):
    root = _tree(tmp_path)
    _inventory(root, [{"id": "demo-4", "state": "unjudged", "why": "no", "who": "reviewer"}])
    state, problems = objective_status.criterion_unjudged(root)
    assert state == "fail"
    assert len(problems) == 2


def test_a_contract_without_a_basis_is_a_failure(tmp_path):
    root = _tree(tmp_path)
    _basis_baseline(root, [])
    _contract(root, "scirel.demo.asset", {"scope": ["x"]})
    state, problems = objective_status.criterion_evidence(root)
    assert state == "fail"
    assert "no verification.basis" in problems[0]


def test_a_baselined_contract_is_a_failure(tmp_path):
    root = _tree(tmp_path)
    _basis_baseline(root, [{"asset_id": "scirel.demo.asset", "reason": "not migrated"}])
    _contract(root, "scirel.demo.asset", {"basis": {"kind": "closed-form", "statement": "x"}})
    state, problems = objective_status.criterion_evidence(root)
    assert state == "fail"
    assert "still baselined" in problems[0]


def test_the_real_repository_has_no_failure():
    results = objective_status.report()
    assert [item["criterion"] for item in results if item["state"] == "fail"] == []


def test_the_cli_exits_zero_when_nothing_fails(capsys):
    assert objective_status.main([]) == 0
    assert "not-observed is not a pass." in capsys.readouterr().out
